"""Glosario del proyecto Pulsar — términos, siglas y abreviaciones (Sesiones 27-28).

Referencia consolidada de toda la terminología usada en el dashboard: programas del
Coordinador (PCP/PID/CMG), magnitudes eléctricas, variables meteorológicas, modelos
FV/eólico, BESS, IA/ML (forecast probabilístico, MILP, soiling) y fuentes de datos.
Solo lectura, sin Plotly. Buscable.
"""
import streamlit as st

AES_TEXTO  = "#1A1F36"
AES_MUTED  = "#6B7280"
AES_AZUL   = "#3B4CE8"
AES_GRIS   = "#F5F7FA"
AES_BORDE  = "#E5E7EB"
AES_BLANCO = "#FFFFFF"

# (término, definición) por categoría
GLOSARIO: dict[str, list[tuple[str, str]]] = {
    "Coordinador y programación (CEN)": [
        ("CEN", "Coordinador Eléctrico Nacional. Organismo que opera el SEN y publica las APIs de datos (planes SIP y Operaciones)."),
        ("SEN", "Sistema Eléctrico Nacional de Chile. La red interconectada que coordina el CEN."),
        ("SIP", "Sistema de Información Pública. Plan de la API CEN (sipub.api.coordinador.cl) con datos públicos; usa CEN_USER_KEY."),
        ("Operaciones", "Plan de la API CEN (operacion.api.coordinador.cl) para datos operacionales (ej. SSCC); usa CEN_OPS_KEY."),
        ("PCP", "Programa de Coordinación / programa diario. Generación y CMG que el CEN programa el día anterior (D-1) para el día siguiente. Línea ámbar en las series."),
        ("PID", "Programa Intra-Día. Reprograma que ajusta el PCP dentro del mismo día (00-23 h) incorporando la operación en tiempo real. Línea verde punteada en las series."),
        ("D-1 / D+1", "Día anterior / día siguiente respecto a la fecha de operación. El PCP se declara en D-1."),
        ("fecha_programa", "Fecha del programa (PCP o PID) que originó un valor. Se conserva el programa más reciente por hora."),
        ("CMG", "Costo Marginal. Costo (USD/MWh) de suministrar 1 MWh adicional al sistema en una barra y hora dadas. Define el precio de la energía."),
        ("CMG online", "CMG en tiempo real publicado por el CEN (feed JSON S3, actualiza ~15 min). Respaldo: endpoint 8 barras."),
        ("CMG programado", "Proyección horaria del CMG futuro por barra (programa PCP/PID). Útil para anticipar ingresos y arbitraje BESS."),
        ("Demanda PID", "Consumo proyectado del SEN (MW) por hora y zona, según el programa intra-día. Se agrega por zona (Norte/Centro/Centro Sur/Sur)."),
        ("Nodo / Barra", "Punto de la red (subestación 220 kV) donde se mide el CMG y la demanda. Ej: CRUCERO_______220, CHARRUA_______220."),
        ("Zona (SEN)", "Agrupación geográfica del sistema: Norte (parques solares), Centro, Centro Sur (parques eólicos), Sur."),
        ("SSCC", "Servicios Complementarios. Recursos que aportan los generadores para la seguridad del sistema (reserva, control de tensión/frecuencia)."),
        ("Limitación de transmisión", "Restricción de la red que obliga a reducir la inyección de un parque (curtailment). Se publica con potencia pendiente y estado."),
        ("Curtailment / Vertimiento", "Energía renovable que no se inyecta por restricción de red o CMG cero/negativo (sobreoferta)."),
        ("llave_opreal / llave_gen / llave_dem", "Identificadores de la API CEN para gen. real, gen. programada y demanda respectivamente, por unidad/punto."),
    ],
    "Generación y magnitudes eléctricas": [
        ("Gen. real", "Generación efectivamente inyectada por el parque (medición CEN, endpoint gen-real/v3), en MW."),
        ("MW", "Megawatt. Unidad de potencia instantánea."),
        ("MWh", "Megawatt-hora. Energía: potencia × tiempo. 1 MW durante 1 h = 1 MWh."),
        ("Pmax bruta", "Potencia máxima instalada del parque (config), en MW. Usada en el modelo FV."),
        ("Pmax neta CEN", "Potencia máxima neta aceptada por el CEN (carta). Base del Factor de Planta (PMAX_FP)."),
        ("FP (Factor de Planta)", "Gen. real / Pmax neta × 100. Porcentaje de la capacidad efectivamente utilizada."),
        ("Desvío vs PCP", "(Gen real − PCP) / PCP × 100, a la misma hora. Verde ≤15%, ámbar ≤25%, rojo >25%."),
        ("Desvío vs PID", "Comparación análoga contra el reprograma intra-día (PID)."),
        ("Ingreso estimado", "Gen. real × CMG del nodo, en USD por hora. Aproxima el ingreso de mercado spot."),
        ("ERNC", "Energías Renovables No Convencionales (solar FV, eólica). El portfolio de AES Andes cubierto por Pulsar."),
        ("FV", "Fotovoltaica. Tecnología solar de los 6 parques del norte."),
    ],
    "Solar FV y meteorología": [
        ("GHI", "Global Horizontal Irradiance (W/m²). Radiación solar total sobre superficie horizontal."),
        ("DNI", "Direct Normal Irradiance. Radiación directa perpendicular al sol."),
        ("DHI", "Diffuse Horizontal Irradiance. Radiación difusa del cielo."),
        ("GTI / POA", "Global Tilted Irradiance / Plane of Array. Radiación sobre el plano del panel (inclinado/seguidor)."),
        ("Tracker (seguidor 1-eje)", "Estructura que gira el panel siguiendo al sol. Ganancia ~1.18 (TRACKER_GAIN) sobre el plano fijo."),
        ("Stow", "Posición horizontal de protección del tracker ante viento fuerte (≥16 m/s, TRACKER_STOW_WIND_MS). El POA cae a GHI."),
        ("Disponibilidad (η_disp)", "Derate por mantenimiento/fallas aplicado al modelo FV (0.80, TRACKER_AVAIL)."),
        ("Temp. de celda (Tc)", "Temperatura de la celda FV (modelo NOCT ajustado por viento). Reduce la potencia ~0.4%/°C sobre 25 °C."),
        ("NOCT", "Nominal Operating Cell Temperature (~45 °C). Constante del modelo térmico del panel."),
        ("γ (gamma)", "Coeficiente de temperatura del panel: −0.4 %/°C (PANEL_GAMMA). Pérdida de potencia por calor."),
        ("Modelo FV", "Potencia estimada del parque a partir de POA, Tc y disponibilidad. Compara contra la gen. real."),
        ("Camanchaca", "Neblina costera baja del norte. Nubosidad baja >60% con cielo total <35% → caída de GHI."),
        ("Nubosidad baja / total", "Porcentaje de cielo cubierto por nubes bajas / por todas las nubes (Open-Meteo)."),
    ],
    "Eólica": [
        ("Viento hub (100 m)", "Velocidad del viento a la altura del buje de la turbina (~100 m), en m/s. Insumo del modelo eólico."),
        ("Wind shear (α)", "Exponente de la ley de potencia que describe cómo crece el viento con la altura. Acotado a [−0.10, 0.60]."),
        ("Cut-in", "Velocidad mínima de viento para que la turbina genere (~3 m/s)."),
        ("Rated", "Velocidad a la que la turbina alcanza su potencia nominal (~12 m/s)."),
        ("Cut-out", "Velocidad máxima; sobre ella la turbina se detiene por seguridad (~25 m/s; Vestas V150: 24.5)."),
        ("Curva de potencia", "Relación viento→potencia por modelo de turbina (Vestas V150, Nordex N149). Definida por parque."),
        ("Densidad del aire (ρ)", "Masa de aire por volumen (kg/m³), función de temperatura y presión. P ∝ ρ en el modelo eólico."),
        ("Ráfaga (gust)", "Pico instantáneo de viento. Relevante para stow y cut-out."),
        ("Modelo eólico", "Potencia estimada desde el viento al hub, densidad del aire y la curva de potencia del parque."),
    ],
    "BESS (almacenamiento)": [
        ("BESS", "Battery Energy Storage System. Sistema de baterías asociado a los parques solares de AES."),
        ("Inyección / Descarga", "Energía que el BESS entrega al sistema (potencia_neta > 0)."),
        ("Retiro / Carga", "Energía que el BESS toma del sistema para almacenar (potencia_neta < 0)."),
        ("Potencia neta", "Inyección − retiro. Positiva descargando, negativa cargando."),
        ("SoC", "State of Charge. Estado de carga estimado por integración del flujo neto."),
        ("Ciclos equivalentes", "Energía descargada / capacidad. Mide el uso/desgaste de la batería."),
        ("Arbitraje", "Cargar con CMG bajo y descargar con CMG alto para capturar el spread de precio."),
        ("Duración (h)", "Horas a potencia nominal que dura la energía del BESS (BESS_HORAS; ej. AS2B 4.95 h, AS3 3 h)."),
    ],
    "Fuentes de datos y stack": [
        ("Open-Meteo", "API meteorológica gratuita (forecast 7 d, histórico ERA5). Radiación, viento, temperatura, nubosidad."),
        ("NASA POWER", "Fuente satelital de GHI/temp/viento para validar el recurso solar. Rezago real ~2-3 meses (~85 días)."),
        ("ERA5 / Archive API", "Reanálisis histórico de Open-Meteo (archive-api) usado para radiación pasada."),
        ("Supabase", "Base de datos PostgreSQL (vía REST API supabase-py) donde se almacenan todas las series."),
        ("RLS", "Row Level Security. Política de Supabase; el anon key necesita política SELECT explícita para leer."),
        ("service_role / anon key", "Llaves Supabase: service_role escribe (adquisición), anon solo lee (frontend)."),
        ("GitHub Actions", "Cron que ejecuta la adquisición: horaria (:10), potencia 30 min (:25/:55), PID (:40)."),
        ("Streamlit", "Framework del dashboard (Python). Desplegado en Streamlit Cloud."),
        ("ML / RandomForest", "Modelos de aprendizaje que predicen gen. desde meteo y detectan anomalías/eficiencia."),
        ("TZ_CHILE", "Zona horaria America/Santiago (ZoneInfo). Todos los fecha_hora se guardan en hora civil de Chile."),
    ],
    "Inteligencia Artificial y modelos (ML)": [
        ("IA", "Inteligencia Artificial. Término amplio que incluye el Machine Learning y la optimización. Pulsar usa IA en ambos sentidos."),
        ("ML (Machine Learning)", "Aprendizaje automático: modelos que aprenden patrones de los datos (clima→generación, etc.). Es una rama de la IA."),
        ("Deep Learning", "Sub-rama del ML basada en redes neuronales (CNN, RNN/LSTM, Transformers). NO se usa en Pulsar: con ~115 días de datos, el gradient boosting rinde mejor. Quedaría para nowcasting de nubes con CNN a futuro."),
        ("Forecast puntual", "Pronóstico de un solo valor por hora (ej. RandomForest meteo→gen). Responde '¿cuánto?', no '¿con qué incertidumbre?'."),
        ("Forecast probabilístico", "Pronóstico que entrega un rango (banda P10–P50–P90) en vez de un número. Permite declarar al CEN y gestionar desvíos con incertidumbre."),
        ("Cuantil / Percentil", "Valor bajo el cual cae un % de los casos. P10 = solo 10% de las horas generan menos; P90 = 90%. P50 = mediana."),
        ("P10 / P50 / P90", "Escenarios del forecast probabilístico: P10 pesimista, P50 central (más probable), P90 optimista. Entre P10 y P90 cae el 80% de los casos."),
        ("Banda de confianza", "Rango P10–P90. 'Con 80% de confianza la generación caerá dentro de esta banda'."),
        ("Cobertura", "Métrica clave del forecast probabilístico: % de horas reales que caen dentro de la banda P10–P90. Ideal ≈ 80%."),
        ("Pinball loss", "Métrica de calidad de un cuantil pronosticado (menor = mejor). Penaliza estar por encima o por debajo del cuantil objetivo."),
        ("LightGBM", "Algoritmo de gradient boosting (árboles) usado para el forecast probabilístico cuantílico. Rápido y preciso en datos tabulares."),
        ("Gradient boosting", "Técnica ML que combina muchos árboles débiles en secuencia, cada uno corrigiendo el error del anterior. Base de LightGBM."),
        ("RandomForest", "Ensemble que promedia muchos árboles de decisión sobre submuestras. Usado en el forecast puntual, anomalías y CMG."),
        ("CQR (calibración conformal)", "Conformalized Quantile Regression. Ajusta el ancho de la banda contra un set de calibración para que la cobertura empírica alcance el 80% real. Corrige la subcobertura del viento."),
        ("R²", "Coeficiente de determinación. Varianza explicada por el modelo: 1.0 = perfecto, 0 = igual que la media, <0 = peor."),
        ("MAE", "Mean Absolute Error. Error absoluto medio del pronóstico, en MW. Cuánto se equivoca en promedio."),
        ("IsolationForest", "Algoritmo no supervisado que aísla observaciones raras. Detecta horas con combinaciones atípicas de clima+generación."),
        ("KMeans / Clustering", "Agrupa observaciones similares. En eficiencia, separa regímenes de operación (alta/media/baja)."),
        ("Feature / Variable", "Cada entrada del modelo (GHI, viento, hora, etc.). 'Importancia de variables' = cuánto pesa cada una."),
        ("Hora seno/coseno", "Codificación cíclica de la hora del día para que el modelo entienda que las 23h y las 0h están juntas."),
        ("MILP / Programación lineal", "Optimización matemática que halla la mejor decisión sujeta a restricciones. Usada para el arbitraje óptimo del BESS. Es IA en sentido amplio, no ML."),
        ("Optimizador BESS", "Calcula el cronograma óptimo de carga/descarga sobre el CMG futuro para maximizar ingreso, respetando SoC, eficiencia y ciclos."),
        ("Round-trip (η)", "Eficiencia de ida y vuelta del BESS: la energía que sale / la que entró (~85%). El resto se pierde al cargar/descargar."),
        ("Performance Ratio (PR)", "Generación real / generación teórica del modelo. PR más bajo = pérdidas (suciedad, sombras, limitaciones)."),
        ("Soiling", "Pérdida de generación FV por suciedad acumulada (polvo del desierto). Se recupera con lluvia o lavado."),
        ("Soiling ratio", "Índice diario de limpieza: PR normalizado contra el mejor estado reciente del parque (P90). 1.0 = limpio, <1.0 = sucio/subrendimiento."),
        ("Backtest", "Validación del modelo sobre datos históricos no usados en el entrenamiento, para medir su precisión real."),
        ("Suncast", "Plataforma comercial chilena de pronóstico ERNC (competidor de referencia). Usa ML clásico; ofrece soiling y servicios para PMGD."),
    ],
    "Parques del portfolio": [
        ("Solares FV (Norte)", "AS1 Andes Solar I, AS2A, AS2B, AS3, AS4 (Atacama), BOL Bolero (Sierra Gorda) y CRI PFV Cristales (300 MW, EN_REVISION)."),
        ("Eólicos (Sur)", "CL Campo Lindo, OLM Los Olmos, STM San Matías, MSM Mesamávida (Biobío) y CUR Los Cururos (Coquimbo). ~426 MW netos."),
        ("Pulsar", "Nombre del dashboard (enfoque en predicción). Cubre los parques ERNC de AES Andes (FV norte + eólicos sur)."),
    ],
}


_GLOSARIO_PASSWORD = "lens"


def render_tab_glosario() -> None:
    # Acceso restringido temporalmente: el glosario queda oculto tras clave.
    if not st.session_state.get("glosario_ok", False):
        st.markdown(
            f"<div style='font-size:18px;font-weight:800;color:{AES_TEXTO};margin:0 0 4px'>"
            f"Glosario del proyecto</div>",
            unsafe_allow_html=True,
        )
        st.caption("Sección protegida. Ingresa la clave para acceder.")
        clave = st.text_input("Clave", type="password", key="glosario_clave",
                              label_visibility="collapsed", placeholder="Clave de acceso")
        if clave:
            if clave == _GLOSARIO_PASSWORD:
                st.session_state["glosario_ok"] = True
                st.rerun()
            else:
                st.error("Clave incorrecta.")
        return

    st.markdown(
        f"<div style='font-size:18px;font-weight:800;color:{AES_TEXTO};margin:0 0 4px'>"
        f"Glosario del proyecto</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Términos, siglas y abreviaciones usados en Pulsar hasta la fecha. "
        "Usa el buscador para filtrar por palabra clave."
    )

    q = st.text_input("Buscar término", placeholder="ej: PID, CMG, shear, BESS...",
                       label_visibility="collapsed", key="glosario_buscar").strip().lower()

    n_mostrados = 0
    for categoria, terminos in GLOSARIO.items():
        if q:
            filtrados = [(t, d) for t, d in terminos if q in t.lower() or q in d.lower()]
        else:
            filtrados = terminos
        if not filtrados:
            continue
        n_mostrados += len(filtrados)

        st.markdown(
            f"<div style='font-size:11px;font-weight:700;color:{AES_AZUL};text-transform:uppercase;"
            f"letter-spacing:1px;margin:18px 0 8px'>{categoria}</div>",
            unsafe_allow_html=True,
        )
        filas = ""
        for termino, definicion in filtrados:
            filas += (
                f"<div style='display:grid;grid-template-columns:200px 1fr;gap:16px;"
                f"padding:8px 0;border-bottom:1px solid {AES_BORDE}'>"
                f"<div style='font-weight:700;color:{AES_TEXTO};font-size:12.5px'>{termino}</div>"
                f"<div style='color:{AES_MUTED};font-size:12.5px;line-height:1.55'>{definicion}</div>"
                f"</div>"
            )
        st.markdown(
            f"<div style='background:{AES_BLANCO};border:1px solid {AES_BORDE};"
            f"border-radius:10px;padding:6px 18px'>{filas}</div>",
            unsafe_allow_html=True,
        )

    if q and n_mostrados == 0:
        st.info(f"Sin coincidencias para «{q}».")
