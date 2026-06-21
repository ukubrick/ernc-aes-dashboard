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
    DIAS_VENTANA, DIAS_VENTANA_LIM,
)

_KEY_SIP: str | None = None
_KEY_OPS: str | None = None

# Sesión HTTP reutilizable: reusa la conexión TCP/TLS entre llamadas (más rápido y
# estable que abrir un socket nuevo por request).
_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/json"})


def _get_keys():
    global _KEY_SIP, _KEY_OPS
    if _KEY_SIP is None:
        _KEY_SIP = os.environ["CEN_USER_KEY"]
    if _KEY_OPS is None:
        _KEY_OPS = os.environ["CEN_OPS_KEY"]
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
    key_sip, _ = _get_keys()
    if start_date is None or end_date is None:
        start_date, end_date = _ventana_fechas()

    # Construir índice inverso: llave_gen → código de parque
    llave_a_parque: dict[str, str] = {}
    for parque, llaves in LLAVES_GEN_PROG.items():
        for llave in llaves:
            llave_a_parque[llave] = parque

    url = f"{API_BASE_SIP}/generacion-programada-pcp/v4/findByDate"
    registros = []
    page = 1

    while True:
        params = {
            "startDate": start_date,
            "endDate":   end_date,
            "limit":     5000,
            "page":      page,
            "user_key":  key_sip,
        }
        data = _get_with_retry(url, params)
        items = data.get("data", data) if isinstance(data, dict) else data

        if not items:
            break

        for item in items:
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

        # API v4 usa "totalPages" (no "total") — controlar paginación con eso
        total_pages = data.get("totalPages", 1) if isinstance(data, dict) else 1
        if page >= total_pages:
            break
        page += 1
        print(f"[PCP] Página {page - 1}/{total_pages} procesada — {len(registros)} registros acumulados")

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
