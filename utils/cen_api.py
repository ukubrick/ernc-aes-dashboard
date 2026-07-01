import os
import time
import random
import requests
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from config import (
    API_BASE_SIP, API_BASE_OPS, CMG_S3_URL,
    TZ_CHILE, ID_CENTRAL, LLAVES_OPREAL, LLAVES_GEN_PROG,
    NOMBRE_DISPLAY, LLAVES_SSCC, PMAX,
    DIAS_VENTANA, DIAS_VENTANA_LIM, DIAS_VENTANA_PID,
    CMG_PROG_LLAVE_A_NODO, CMG_8B_NOMBRE_A_NODO,
    DEMANDA_ZONAS_EXCLUIR,
)

_KEY_SIP: str | None = None
_KEY_OPS: str | None = None

# Sesión HTTP reutilizable: reusa la conexión TCP/TLS entre llamadas (más rápido y
# estable que abrir un socket nuevo por request).
_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/json"})

# Presupuesto de tiempo (segundos) para los endpoints que paginan TODO el sistema
# (PCP, PID, demanda, CMG programado). Si la API CEN se degrada y una página tarda,
# el loop corta y devuelve lo parcial en vez de colgar el cron entero (el upsert de
# ventana móvil se auto-corrige en la corrida siguiente). Ver workflow timeout-minutes.
PAGINADO_MAX_SEG = 720  # 12 min por endpoint


def _get_keys():
    # CEN_OPS_KEY es opcional: solo la usa SSCC (plan Operaciones). Scripts que solo
    # consumen SIP (ej. Adquisicion_potencia_ernc: gen-real + BESS) corren sin ella.
    global _KEY_SIP, _KEY_OPS
    if _KEY_SIP is None:
        _KEY_SIP = os.environ["CEN_USER_KEY"]
    if _KEY_OPS is None:
        _KEY_OPS = os.environ.get("CEN_OPS_KEY", "")
    return _KEY_SIP, _KEY_OPS


def _get_with_retry(url: str, params: dict, max_retries: int = 4, timeout: int = 40) -> dict:
    """GET resiliente.

    - Reintenta en 429 (rate limit) y 5xx, además de errores de red/timeout.
    - En 429 respeta el header `Retry-After` si viene; si no, backoff exponencial.
    - Backoff con jitter (8s, 16s, 32s ± aleatorio) para no sincronizar reintentos.
    - 4xx distintos de 429 fallan rápido (no tiene sentido reintentar un 400/404).
    """
    last_exc = None
    for attempt in range(max_retries):
        try:
            r = _SESSION.get(url, params=params, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                retry_after = r.headers.get("Retry-After")
                wait = (float(retry_after) if retry_after and retry_after.isdigit()
                        else 8 * (2 ** attempt) + random.uniform(0, 3))
                print(f"[RETRY] {r.status_code} en {url} (intento {attempt + 1}). Esperando {wait:.0f}s...")
                last_exc = requests.HTTPError(f"{r.status_code}")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except (requests.ConnectionError, requests.Timeout) as e:
            last_exc = e
            wait = 8 * (2 ** attempt) + random.uniform(0, 3)
            print(f"[RETRY] Red fallida ({url}) intento {attempt + 1}: {e}. Esperando {wait:.0f}s...")
            time.sleep(wait)
    raise last_exc if last_exc else RuntimeError(f"GET agotó reintentos: {url}")


def _ventana_fechas(dias: int = DIAS_VENTANA) -> tuple[str, str]:
    """Retorna (startDate, endDate) en formato YYYY-MM-DD para la ventana de adquisición.
    endDate = mañana para capturar datos del día actual aunque la API publique con delay."""
    hoy = datetime.now(TZ_CHILE).date()
    return (hoy - timedelta(days=dias - 1)).isoformat(), (hoy + timedelta(days=1)).isoformat()


def _paginar_sip(path: str, start_date: str, end_date: str, limit: int = 5000,
                 tag: str = "CEN", timeout: int = 90, max_seg: int = PAGINADO_MAX_SEG):
    """Generador que pagina un endpoint v4 del SIP completo (campo `data` + `totalPages`).

    Centraliza el patrón "paginar todo el sistema y filtrar local" que comparten
    PCP, PID, demanda, CMG programado, instrucciones y SSCC programados. Respeta el
    presupuesto de tiempo: si la API se degrada, corta y el caller queda con datos
    parciales (el upsert de ventana móvil se auto-corrige en la corrida siguiente).
    Yields: cada item del feed.
    """
    key_sip, _ = _get_keys()
    url = f"{API_BASE_SIP}{path}"
    page = 1
    _t0 = time.monotonic()
    while True:
        if time.monotonic() - _t0 > max_seg:
            print(f"[{tag}] Presupuesto de tiempo agotado en página {page} — parcial.")
            return
        params = {
            "startDate": start_date, "endDate": end_date,
            "limit": limit, "page": page, "user_key": key_sip,
        }
        data = _get_with_retry(url, params, timeout=timeout)
        items = data.get("data", []) if isinstance(data, dict) else []
        if not items:
            return
        yield from items
        total_pages = data.get("totalPages") if isinstance(data, dict) else None
        if total_pages is None or page >= int(total_pages):
            return
        page += 1
        if page % 10 == 0:
            print(f"[{tag}] Página {page}/{total_pages}...")


def _hora_cen_a_dt(fecha_hora_str: str, hora_cen: int) -> str:
    """
    Convierte fecha_hora CEN y hora (1-24) a string 'YYYY-MM-DD HH:MM:SS' (hora 0-based).
    La API devuelve hora en convención 1-24; convertimos a 0-23 para el sistema.
    """
    fecha = fecha_hora_str[:10]
    hora_0based = hora_cen - 1
    return f"{fecha} {hora_0based:02d}:00:00"


# ── Generación Real ────────────────────────────────────────────────────────────

def fetch_gen_real(parque: str, start_date: str = None, end_date: str = None) -> list[dict]:
    """
    Descarga generación real para un parque desde gen-real/v3.
    Retorna lista de registros normalizados listos para upsert_generacion_real().
    """
    key_sip, _ = _get_keys()
    if start_date is None or end_date is None:
        start_date, end_date = _ventana_fechas()

    id_central = ID_CENTRAL[parque]
    llave_opreal = LLAVES_OPREAL[parque]
    url = f"{API_BASE_SIP}/generacion-real/v3/findByDate"

    registros = []
    page = 1
    while True:
        params = {
            "startDate":   start_date,
            "endDate":     end_date,
            "idCentral":   id_central,
            "pageSize":    5000,
            "page":        page,
            "user_key":    key_sip,
        }
        data = _get_with_retry(url, params)
        items = data.get("data", data) if isinstance(data, dict) else data

        if not items:
            break

        for item in items:
            # Filtrar solo registros del parque (API también devuelve BESS asociados)
            if item.get("llave_opreal") != llave_opreal:
                continue

            hora_cen = int(item.get("hora", 1))
            fecha_hora = _hora_cen_a_dt(item["fecha_hora"], hora_cen)

            # Saneamiento: descartar valores físicamente imposibles (> 110% de Pmax).
            # Los demás se auto-corrigen al re-descargar la ventana (upsert horario).
            gen_mw = item.get("gen_real_mw", 0.0)
            _pmax_parque = PMAX.get(parque)
            if gen_mw is not None and _pmax_parque and gen_mw > _pmax_parque * 1.10:
                print(f"[GEN-REAL] Valor anómalo descartado {parque} {fecha_hora}: {gen_mw} > Pmax {_pmax_parque}")
                continue

            registros.append({
                "parque":          parque,
                "id_central":      item.get("id_central"),
                "llave_opreal":    item.get("llave_opreal"),
                "central":         item.get("central"),
                "gen_real_mw":     gen_mw,
                "potencia_max":    item.get("potencia_maxima"),
                "factor_ernc":     item.get("factor_ernc"),
                "valor_ernc":      item.get("valor_ernc"),
                "tipo_tecnologia": item.get("tipo_tecnologia"),
                "fecha_hora":      fecha_hora,
                "hora":            hora_cen - 1,
            })

        # Paginación robusta: la API v3 puede devolver "totalPages" o "total".
        # Si no hay metadato, cortar cuando la página viene incompleta (< pageSize).
        if isinstance(data, dict) and data.get("totalPages") is not None:
            if page >= data["totalPages"]:
                break
        elif isinstance(data, dict) and data.get("total") is not None:
            if page * 5000 >= data["total"]:
                break
        elif len(items) < 5000:
            break
        page += 1

    return registros


def fetch_gen_bess(start_date: str = None, end_date: str = None) -> list[dict]:
    """
    Descarga generación de los BESS de AES Andes desde gen-real/v3.

    Los BESS aparecen con id_central=None, por lo que NO se pueden filtrar por
    idCentral: hay que recorrer el feed completo y quedarse con las llaves de
    BESS_LLAVE_MAP. Se agregan inyección y retiro por (bess, fecha_hora) y se
    calcula la potencia neta (inyeccion - retiro). Ventana corta (2 días) para
    acotar el costo del scan completo.

    Retorna lista de registros para upsert_generacion_bess().
    """
    from config import BESS_LLAVE_MAP, BESS
    key_sip, _ = _get_keys()
    if start_date is None or end_date is None:
        start_date, end_date = _ventana_fechas(2)

    url = f"{API_BASE_SIP}/generacion-real/v3/findByDate"
    # acc[(bess, fecha_hora)] = {"iny": x, "ret": y}
    acc: dict[tuple[str, str], dict[str, float]] = {}

    page = 1
    while True:
        params = {
            "startDate": start_date, "endDate": end_date,
            "pageSize": 5000, "page": page, "user_key": key_sip,
        }
        data = _get_with_retry(url, params)
        items = data.get("data", data) if isinstance(data, dict) else data
        if not items:
            break

        for item in items:
            mapeo = BESS_LLAVE_MAP.get(item.get("llave_opreal"))
            if not mapeo:
                continue
            cod, flujo = mapeo
            hora_cen = int(item.get("hora", 1))
            fecha_hora = _hora_cen_a_dt(item["fecha_hora"], hora_cen)
            val = item.get("gen_real_mw") or 0.0
            slot = acc.setdefault((cod, fecha_hora), {"iny": 0.0, "ret": 0.0})
            slot[flujo] += float(val)

        if isinstance(data, dict) and data.get("totalPages") is not None:
            if page >= data["totalPages"]:
                break
        elif len(items) < 5000:
            break
        page += 1

    registros = []
    for (cod, fecha_hora), v in acc.items():
        iny = round(v["iny"], 4)
        ret = round(v["ret"], 4)
        registros.append({
            "bess":             cod,
            "parque":           BESS[cod]["parque"],
            "fecha_hora":       fecha_hora,
            "inyeccion_mw":     iny,
            "retiro_mw":        ret,
            "potencia_neta_mw": round(iny - ret, 4),
        })
    print(f"[BESS] {len(registros)} registros de {len(BESS)} BESS")
    return registros


def fetch_gen_real_todos(start_date: str = None, end_date: str = None) -> list[dict]:
    """Descarga generación real para los 11 parques."""
    if start_date is None or end_date is None:
        start_date, end_date = _ventana_fechas()
    todos = []
    for parque in ID_CENTRAL:
        try:
            recs = fetch_gen_real(parque, start_date, end_date)
            todos.extend(recs)
            print(f"[GEN-REAL] {NOMBRE_DISPLAY[parque]}: {len(recs)} registros")
        except Exception as e:
            print(f"[GEN-REAL] ERROR {parque}: {e}")
    return todos


# ── Generación Programada PCP ─────────────────────────────────────────────────

def fetch_gen_programada(start_date: str = None, end_date: str = None) -> list[dict]:
    """
    Descarga generación programada PCP para todos los parques.
    La API NO filtra por idCentral — se descarga todo y filtra local por LLAVES_GEN_PROG.
    """
    if start_date is None or end_date is None:
        start_date, end_date = _ventana_fechas()

    # Construir índice inverso: llave_gen → código de parque
    llave_a_parque: dict[str, str] = {}
    for parque, llaves in LLAVES_GEN_PROG.items():
        for llave in llaves:
            llave_a_parque[llave] = parque

    registros = []
    for item in _paginar_sip("/generacion-programada-pcp/v4/findByDate",
                             start_date, end_date, tag="PCP"):
        # Campo confirmado en API v4: "llave_gen"
        llave = item.get("llave_gen", "")
        parque = llave_a_parque.get(llave)
        if parque is None:
            continue

        # PCP v4: fecha_hora viene como "YYYY-MM-DD HH:MM:SS" ya en 0-based
        fecha_hora_raw = item.get("fecha_hora", "")
        fecha_hora = fecha_hora_raw[:19] if fecha_hora_raw else ""
        hora_0 = int(fecha_hora[11:13]) if len(fecha_hora) >= 13 else 0

        registros.append({
            "parque":                   parque,
            "llave_gen":                llave,
            "gen_programada_mw":        item.get("gen_programada_mw"),
            "capacidad_disponible_mw":  item.get("capacidad_disponible_mw"),
            "costo_generacion_usd":     item.get("costo_generacion_usd"),
            "fecha_hora":               fecha_hora,
            "hora":                     hora_0,
            "fecha_programa":           item.get("fecha_programa"),
            "fuente":                   "CEN_PCP",
        })

    return registros


# ── Generación programada PID (reprograma intra-día) ─────────────────────────────

def fetch_gen_programada_pid(start_date: str = None, end_date: str = None) -> list[dict]:
    """
    Descarga generación programada PID para los parques del portfolio.

    El PID (Programa Intra-Día) ajusta el PCP dentro del día (00-23h) con la
    operación real. Mismo esquema que el PCP: campo `llave_gen`, NO filtra por
    idCentral → se pagina todo y se filtra local por LLAVES_GEN_PROG. Se conserva
    el programa más reciente (mayor `fecha_programa`) por (parque, fecha_hora).
    Va a la misma tabla generacion_programada_ernc con fuente='CEN_PID'.
    """
    if start_date is None or end_date is None:
        start_date, end_date = _ventana_fechas(DIAS_VENTANA_PID)

    llave_a_parque: dict[str, str] = {}
    for parque, llaves in LLAVES_GEN_PROG.items():
        for llave in llaves:
            llave_a_parque[llave] = parque

    mejor: dict[tuple[str, str], dict] = {}   # (parque, fecha_hora) → registro
    for item in _paginar_sip("/generacion-programada-pid/v4/findByDate",
                             start_date, end_date, tag="PID"):
        parque = llave_a_parque.get(item.get("llave_gen", ""))
        if parque is None:
            continue
        fh = (item.get("fecha_hora") or "")[:19]
        if not fh:
            continue
        fprog = item.get("fecha_programa") or ""
        clave = (parque, fh)
        anterior = mejor.get(clave)
        if anterior is None or fprog >= anterior["fecha_programa"]:
            mejor[clave] = {
                "parque":                  parque,
                "llave_gen":               item.get("llave_gen", ""),
                "gen_programada_mw":       item.get("gen_programada_mw"),
                "capacidad_disponible_mw": item.get("capacidad_disponible_mw"),
                "costo_generacion_usd":    item.get("costo_generacion_usd"),
                "fecha_hora":              fh,
                "hora":                    int(fh[11:13]) if len(fh) >= 13 else 0,
                "fecha_programa":          fprog,
                "fuente":                  "CEN_PID",
            }

    return list(mejor.values())


# ── Demanda programada PID por zona del SEN ──────────────────────────────────────

def fetch_demanda_pid(start_date: str = None, end_date: str = None) -> list[dict]:
    """
    Descarga la demanda programada PID y la agrega por (zona, fecha_hora).

    Endpoint: /demanda-programada-pid/v4/findByDate (SIP). Devuelve la demanda
    proyectada (MW) por punto de consumo con campo `zona`. Se suma por zona del SEN
    (excluyendo Argentina y registros sin zona) y se conserva el programa más
    reciente (mayor `fecha_programa`) por (zona, fecha_hora).
    Retorna registros para upsert_demanda().
    """
    if start_date is None or end_date is None:
        start_date, end_date = _ventana_fechas(DIAS_VENTANA_PID)

    # (zona, fecha_hora) → {"mw": suma, "fecha_programa": max}
    acum: dict[tuple[str, str], dict] = {}
    for item in _paginar_sip("/demanda-programada-pid/v4/findByDate",
                             start_date, end_date, limit=4000, tag="DEMANDA"):
        zona = item.get("zona")
        if zona in DEMANDA_ZONAS_EXCLUIR:
            continue
        fh = (item.get("fecha_hora") or "")[:19]
        if not fh:
            continue
        mw = item.get("demanda_prog_mw") or 0.0
        fprog = item.get("fecha_programa") or ""
        clave = (zona, fh)
        cur = acum.get(clave)
        # Si llega un programa más nuevo, se reinicia la suma de esa hora
        if cur is None or fprog > cur["fecha_programa"]:
            acum[clave] = {"mw": float(mw), "fecha_programa": fprog}
        elif fprog == cur["fecha_programa"]:
            cur["mw"] += float(mw)

    registros = []
    for (zona, fh), v in acum.items():
        registros.append({
            "zona":           zona,
            "demanda_mw":     round(v["mw"], 2),
            "fecha_hora":     fh,
            "hora":           int(fh[11:13]) if len(fh) >= 13 else 0,
            "fecha_programa": v["fecha_programa"],
        })
    return registros


# ── CMG ────────────────────────────────────────────────────────────────────────

def fetch_cmg() -> dict:
    """
    Lee el JSON S3 de CMG online. Actualiza cada ~15 min en la fuente.
    Estructura real: {maintenance: bool, data: [{name, horas: [{hora, total}]}]}
    Retorna dict {nombre_nodo: {"nombre": ..., "cmg_usd_mwh": ..., "fecha_hora": ...}}.
    """
    r = requests.get(
        CMG_S3_URL,
        headers={"Referer": "https://www.coordinador.cl/"},
        timeout=15,
    )
    r.raise_for_status()
    payload = r.json()
    items = payload.get("data", [])
    resultado = {}
    for item in items:
        nombre = item.get("name", "")
        horas = item.get("horas", [])
        if horas:
            ultima = horas[-1]  # última entrada disponible (más reciente)
            resultado[nombre] = {
                "nombre":      nombre,
                "cmg_usd_mwh": ultima.get("total"),
                "fecha_hora":  ultima.get("hora"),   # formato "YYYY-MM-DD HH:MM"
            }
    return resultado


def cmg_a_registros(cmg_data: dict, nodos: list[str]) -> list[dict]:
    """
    Convierte el dict de CMG a registros para upsert_cmg().
    nodos: lista de nombres de nodo a guardar (ej. ['CRUCERO_______220']).
    """
    registros = []
    for nodo in nodos:
        item = cmg_data.get(nodo)
        if item:
            # fecha_hora viene como "YYYY-MM-DD HH:MM", normalizar a "YYYY-MM-DD HH:MM:00"
            fh = item["fecha_hora"]
            if len(fh) == 16:
                fh += ":00"
            registros.append({
                "nodo":        nodo,
                "cmg_usd_mwh": item["cmg_usd_mwh"],
                "fecha_hora":  fh,
            })
    return registros


# ── CMG Programado PCP (CMG futuro) ──────────────────────────────────────────────

def fetch_cmg_programado(start_date: str = None, end_date: str = None) -> list[dict]:
    """
    Descarga el CMG programado PCP (proyección día+1 por barra) desde la API SIP.

    Endpoint: /cmg-programado-pcp/v4/findByDate
    - 1-indexado (page=1). NO filtra por barra en el servidor → se pagina todo y se
      filtra local por `llave_cmg` ∈ CMG_PROG_LLAVE_A_NODO. Con limit alto (4000)
      las 8 barras relevantes caben en la página 1.
    - Se conserva el programa más reciente (mayor `fecha_programa`) por (nodo, fecha_hora).
    Retorna registros para upsert_cmg_programado().
    """
    if start_date is None or end_date is None:
        start_date, end_date = _ventana_fechas()

    mejor: dict[tuple[str, str], dict] = {}   # (nodo, fecha_hora) → registro
    for item in _paginar_sip("/cmg-programado-pcp/v4/findByDate",
                             start_date, end_date, limit=4000, tag="CMG-PROG"):
        nodo = CMG_PROG_LLAVE_A_NODO.get(item.get("llave_cmg"))
        if nodo is None:
            continue
        fh = (item.get("fecha_hora") or "").replace("T", " ")[:19]
        if not fh:
            continue
        fprog = item.get("fecha_programa") or ""
        clave = (nodo, fh)
        anterior = mejor.get(clave)
        if anterior is None or fprog >= anterior["fecha_programa"]:
            mejor[clave] = {
                "nodo":           nodo,
                "fecha_hora":     fh,
                "cmg_usd_mwh":    round(float(item.get("cmg_usd_mwh") or 0.0), 4),
                "fecha_programa": fprog,
            }

    return list(mejor.values())


# ── CMG Online 8 barras (respaldo API del feed S3) ───────────────────────────────

def fetch_cmg_online_8b() -> list[dict]:
    """
    Descarga el CMG online de las 8 barras desde la API SIP (vía user_key), como
    respaldo del feed S3 cuando éste falla o está en mantenimiento.

    Endpoint: /costos-marginales-online-8b/v4/findAll
    Estructura: {fecha, barras:[{nombre, valores:[{fecha(epoch ms), valor}]}]}.
    Se mapea cada barra a su nodo (CMG_8B_NOMBRE_A_NODO) y se devuelven todos los
    puntos horarios para upsert en cmg_ernc (mismos nodos que el S3).
    """
    key_sip, _ = _get_keys()
    url = f"{API_BASE_SIP}/costos-marginales-online-8b/v4/findAll"
    data = _get_with_retry(url, {"user_key": key_sip}, timeout=40)
    barras = data.get("barras", []) if isinstance(data, dict) else []

    registros = []
    for barra in barras:
        nodo = CMG_8B_NOMBRE_A_NODO.get(barra.get("nombre"))
        if nodo is None:
            continue
        for v in barra.get("valores", []):
            epoch_ms = v.get("fecha")
            valor = v.get("valor")
            if epoch_ms is None or valor is None:
                continue
            dt = datetime.fromtimestamp(epoch_ms / 1000, TZ_CHILE)
            registros.append({
                "nodo":        nodo,
                "cmg_usd_mwh": round(float(valor), 4),
                "fecha_hora":  dt.strftime("%Y-%m-%d %H:%M:%S"),
            })
    return registros


# ── Limitaciones de Transmisión ────────────────────────────────────────────────

def fetch_limitaciones(start_date: str = None, end_date: str = None) -> list[dict]:
    """
    Descarga limitaciones de transmisión y filtra las que afectan a los parques del portfolio.
    """
    key_sip, _ = _get_keys()
    if start_date is None or end_date is None:
        start_date, end_date = _ventana_fechas(DIAS_VENTANA_LIM)

    # Nombres de instalación a buscar (fragmentos — match parcial)
    nombres_parques = {v.upper() for v in LLAVES_OPREAL.values()}

    url = f"{API_BASE_SIP}/limitaciones-transmision/v4/findByDate"
    registros = []
    page = 1
    _PAGE_SIZE = 500   # subir el page size reduce el nº de páginas y de llamadas 429

    # Índice de fragmentos de nombre a buscar dentro de instalacion_nombre.
    # Se quita el prefijo PFV/PE y se normalizan tildes para hacer match parcial robusto.
    def _norm(s: str) -> str:
        return (s.upper()
                .replace("Á", "A").replace("É", "E").replace("Í", "I")
                .replace("Ó", "O").replace("Ú", "U"))

    frag_a_parque = {}
    for codigo, llave in LLAVES_OPREAL.items():
        frag = _norm(llave).replace("PFV ", "").replace("PE ", "").strip()
        frag_a_parque[frag] = codigo

    while True:
        params = {
            "startDate": start_date,
            "endDate":   end_date,
            "limit":     _PAGE_SIZE,
            "page":      page,
            "user_key":  key_sip,
        }
        data = _get_with_retry(url, params)
        items = data.get("data", data) if isinstance(data, dict) else data

        if not items:
            break

        for item in items:
            instalacion = _norm(item.get("instalacion_nombre") or "")
            # Buscar si alguno de nuestros parques aparece en el nombre de la instalación
            parque_match = None
            for frag, codigo in frag_a_parque.items():
                if frag and frag in instalacion:
                    parque_match = codigo
                    break

            if parque_match is None:
                continue

            corr_raw = item.get("correlativo") or item.get("id")
            corr_int = int(float(corr_raw)) if corr_raw is not None else None
            id_str = str(item.get("id") or corr_raw or "")
            registros.append({
                "id":                       id_str,
                "correlativo":              corr_int,
                "parque":                   parque_match,
                "empresa_nombre":           item.get("empresa_nombre"),
                "instalacion_nombre":       item.get("instalacion_nombre"),
                "status":                   item.get("status"),
                "fecha_perturbacion":       item.get("fecha_perturbacion"),
                "fecha_retorno_estimada":   item.get("fecha_retorno_estimada"),
                "fecha_efectiva_retorno":   item.get("fecha_efectiva_retorno"),
                "potencia":                 item.get("potencia"),
                "unidad_medida_potencia":   item.get("unidad_medida_potencia"),
                "produce_indisponibilidad": item.get("produce_indisponibilidad"),
                "afecta_sscc":              item.get("afecta_sscc"),
                "observacion":              item.get("observacion"),
                "created":                  item.get("created"),
                "modified":                 item.get("modified"),
            })

        # Paginación robusta — la API v4 publica "totalPages", no "total".
        if isinstance(data, dict) and data.get("totalPages") is not None:
            if page >= data["totalPages"]:
                break
        elif isinstance(data, dict) and data.get("total") is not None:
            if page * _PAGE_SIZE >= data["total"]:
                break
        elif len(items) < _PAGE_SIZE:
            break
        page += 1
        print(f"[LIM] Página {page - 1} procesada — {len(registros)} limitaciones de parques acumuladas")

    return registros


# ── SSCC ────────────────────────────────────────────────────────────────────────

def fetch_sscc(start_date: str = None, end_date: str = None) -> list[dict]:
    """
    Descarga instrucciones de SSCC desde API Operaciones.
    Filtra solo parques del portfolio (por ahora solo PE San Matías confirmado).
    """
    _, key_ops = _get_keys()
    if start_date is None or end_date is None:
        start_date, end_date = _ventana_fechas()

    url = f"{API_BASE_OPS}/servicios-complementarios/v1"
    params = {
        "initDate":  start_date,
        "endDate":   end_date,
        "page":      0,
        "pageSize":  -1,
        "user_key":  key_ops,
    }
    data = _get_with_retry(url, params)

    # La API de Operaciones usa 'content' y camelCase
    items = data.get("content", data.get("data", []))

    registros = []
    for item in items:
        central_unidad = item.get("centralUnidad", "")
        parque = LLAVES_SSCC.get(central_unidad)
        if parque is None:
            continue

        # Mapeo camelCase → snake_case
        fecha = item.get("fecha", "")[:10]
        registros.append({
            "parque":          parque,
            "fecha":           fecha,
            "inicio_periodo":  item.get("inicioPeriodo"),
            "fin_periodo":     item.get("finPeriodo"),
            "instruccion_sscc": item.get("instruccionSscc"),
            "id_configuracion": item.get("idConfiguracion"),
            "central_unidad":  central_unidad,
            "disponibilidad":  item.get("disponibilidad"),
            "baja":            item.get("baja"),
            "sube":            item.get("sube"),
            "unidad_medida":   item.get("unidadMedida"),
        })

    return registros


# ── Pronóstico de demanda del SEN a 7 días (Sesión 34) ───────────────────────────

def fetch_demanda_pronostico(dias: int = 7) -> list[dict]:
    """
    Descarga el pronóstico de demanda de corto plazo (7 días) del SEN y lo agrega
    a total sistema por hora.

    Endpoint: /pronosticos-demanda-corto-plazo/v4/findByDate (SIP). Publica
    energía horaria (MWh/h ≈ MW medio) POR BARRA — se suma todo por fecha_hora.
    `fecha_hora` ya viene 0-based ("YYYY-MM-DD HH:MM:SS"); el campo `hora` 1-24
    se ignora. Retorna registros para upsert_demanda_pronostico().
    """
    hoy = datetime.now(TZ_CHILE).date()
    start_date = hoy.isoformat()
    end_date = (hoy + timedelta(days=dias)).isoformat()

    acum: dict[str, float] = {}   # fecha_hora → MW total SEN
    for item in _paginar_sip("/pronosticos-demanda-corto-plazo/v4/findByDate",
                             start_date, end_date, limit=4000, tag="DEM-7D"):
        fh = (item.get("fecha_hora") or "")[:19]
        mw = item.get("energia_mwh")
        if not fh or mw is None:
            continue
        acum[fh] = acum.get(fh, 0.0) + float(mw)

    return [{"fecha_hora": fh, "demanda_mw": round(mw, 2)}
            for fh, mw in acum.items()]


# ── Instrucciones operacionales CMG (curtailment ordenado) — Sesión 34 ───────────

def fetch_instrucciones_cmg(start_date: str = None, end_date: str = None) -> list[dict]:
    """
    Descarga las instrucciones operacionales del CEN a los centros de control y
    filtra las de los parques/BESS del portfolio.

    Endpoint: /instrucciones-operacionales-cmg/v4/findByDate (SIP). Los nombres de
    central usan formato corto propio (PFV-ANDES2A, PE-CAMPOLINDO, SAE-CRCA-*) →
    mapeo EXACTO en config.INSTR_CENTRAL_A_PARQUE (match parcial da falsos positivos
    tipo "PFV-MESETADELOSANDES"). Es la fuente para distinguir curtailment ordenado
    de soiling/falla. Retorna registros para upsert_instrucciones().
    """
    from config import INSTR_CENTRAL_A_PARQUE
    if start_date is None or end_date is None:
        start_date, end_date = _ventana_fechas(2)

    registros = []
    for item in _paginar_sip("/instrucciones-operacionales-cmg/v4/findByDate",
                             start_date, end_date, limit=4000, tag="INSTR"):
        parque = INSTR_CENTRAL_A_PARQUE.get(item.get("central") or "")
        if parque is None:
            continue
        fecha = (item.get("fecha") or "")[:10]
        hora = (item.get("hora") or "00:00:00")[:8]
        if not fecha:
            continue
        registros.append({
            "id_instruccion":  item.get("id_instruccion"),
            "parque":          parque,
            "central":         item.get("central"),
            "configuracion":   item.get("configuracion"),
            "fecha_hora":      f"{fecha} {hora}",
            "despacho_mw":     item.get("despacho"),
            "consigna":        item.get("consigna"),
            "instruccion_cmg": item.get("instruccion_cmg"),
            "estado":          item.get("estado"),
            "motivo":          item.get("motivo"),
        })
    return registros


# ── SSCC programados PCP (MW y servicio por central) — Sesión 34 ─────────────────

def fetch_sscc_programado(start_date: str = None, end_date: str = None) -> list[dict]:
    """
    Descarga los servicios complementarios PROGRAMADOS (PCP) de las centrales del
    portfolio: MW de provisión por tipo de servicio (CPF/CSF/CTF ±) y hora.

    Endpoint: /servicios-complementarios-programados-pcp/v4/findByDate (SIP).
    MUY voluminoso (~300k filas/día del sistema completo) → ventana 1 día y
    limit=4000 (~77 páginas). Correr 1 vez/día, NO en el cron horario. Se filtra
    local por `id_central` ∈ ID_CENTRAL del portfolio.
    Retorna registros para upsert_sscc_programado().
    """
    if start_date is None or end_date is None:
        hoy = datetime.now(TZ_CHILE).date()
        start_date = hoy.isoformat()
        end_date = (hoy + timedelta(days=1)).isoformat()

    ids_portfolio = {v for v in ID_CENTRAL.values() if v is not None}
    registros = []
    for item in _paginar_sip("/servicios-complementarios-programados-pcp/v4/findByDate",
                             start_date, end_date, limit=4000, tag="SSCC-PCP"):
        if item.get("id_central") not in ids_portfolio:
            continue
        id_a_parque = {v: k for k, v in ID_CENTRAL.items()}
        registros.append({
            "id":             item.get("id"),
            "parque":         id_a_parque.get(item.get("id_central")),
            "central":        item.get("central"),
            "llave_sscc":     item.get("llave_sscc"),
            "tipo_servicio":  item.get("tipo_servicio"),
            "provision_mw":   item.get("provision_mw"),
            "fecha_hora":     (item.get("fecha_hora") or "")[:19],
            "fecha_programa": item.get("fecha_programa"),
            "barra":          item.get("barra"),
        })
    return registros
