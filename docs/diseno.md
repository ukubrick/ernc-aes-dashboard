# Sistema de diseño visual — detalle completo

> Extraído de CLAUDE.md (2026-07-01). La paleta y reglas esenciales están en CLAUDE.md.

## SISTEMA DE DISEÑO VISUAL (actualizado Sesión 9)

El diseño del dashboard está documentado aquí como referencia para replicar en otros dashboards (ej. CTM).

### Principios generales
- **Fondo**: `#F5F7FA` (gris muy suave), **nunca blanco puro como fondo de página**
- **Cards**: siempre `#FFFFFF` con `border-radius: 10-12px`
- **Sin emojis** en ningún componente
- **Sin comentarios** de "qué hace" en el código — solo comentarios del WHY
- Todo `st.plotly_chart()` lleva `key=` único explícito
- Timezone siempre `America/Santiago` (UTC-3), nunca `timezone.utc`
- **f-strings**: NO usar backslash dentro del f-string (error Python < 3.12) — extraer a variable antes
- **Fuente**: Inter (Google Fonts), pesos 400/500/600/700/800

### Sidebar
```css
/* Gradiente de 3 tonos azul muy oscuro */
background: linear-gradient(160deg, #2530B0 0%, #111540 60%, #0d1035 100%);
box-shadow: 4px 0 20px rgba(0,0,0,0.25);

/* Título empresa */
font-size: 22px; font-weight: 800; color: white; letter-spacing: -0.5px;

/* Etiquetas de sección (SOLAR FV / EÓLICA) */
font-size: 10px; font-weight: 700; color: #4DC8DC;
text-transform: uppercase; letter-spacing: 1.2px;

/* Botón normal */
background: rgba(255,255,255,0.06);
border: 1px solid rgba(255,255,255,0.12);
border-radius: 8px; transition: all 0.20s cubic-bezier(0.4,0,0.2,1);

/* Botón hover */
background: rgba(77,200,220,0.22); border-color: #4DC8DC;
transform: translateX(3px);

/* Botón activo */
background: linear-gradient(90deg, #4DC8DC 0%, #38b5cc 100%);
color: #2530B0; font-weight: 700;
box-shadow: 0 4px 12px rgba(77,200,220,0.40);
```

### KPI cards (métricas Streamlit)
```css
background: #FFFFFF; border-radius: 12px;
border: 1px solid #E5E7EB;
border-top: 4px solid [color por posición];   /* diferenciador visual principal */
box-shadow: 0 2px 12px rgba(59,76,232,0.08);
transition: transform 0.20s ease, box-shadow 0.20s ease;

/* Hover lift */
transform: translateY(-3px);
box-shadow: 0 8px 24px rgba(59,76,232,0.15);

/* Color borde-top por posición (7 KPIs) */
1º Gen Total    → #3B4CE8  azul
2º Solar FV     → #3B4CE8  azul
3º Eólica       → #4DC8DC  cyan
4º Desvío PCP   → #F59E0B  ámbar
5º CMG Crucero  → #9B6FD4  violeta
6º CMG Charrua  → #4DC8DC  cyan
7º Limitaciones → #EF4444  rojo

/* Tipografía interna */
Label:  10px, 700, uppercase, letter-spacing 0.8px, color #6B7280
Valor:  22px, 800, color #1A1F36
Delta:  12px, 600
```

### Tabs
```css
/* Barra contenedora */
background: #FFFFFF; border-bottom: 3px solid #3B4CE8;
border-radius: 8px 8px 0 0; box-shadow: 0 2px 8px rgba(0,0,0,0.05);

/* Tab inactiva */
color: #6B7280; font-size: 13px; font-weight: 500; padding: 9px 18px;
transition: all 0.20s cubic-bezier(0.4,0,0.2,1);

/* Tab activa */
background: linear-gradient(135deg, #3B4CE8 0%, #2530B0 100%);
color: white; font-weight: 700;
box-shadow: 0 -2px 10px rgba(59,76,232,0.30);

/* Contenido del tab */
animation: fadeInUp 0.35s ease both;
```

### Gráficos Plotly
```python
# Configuración estándar en update_layout
fig.update_layout(
    template="plotly_white",
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#F5F7FA",
    transition=dict(duration=500, easing="cubic-in-out"),  # animación entre datos
)

# Colores de trazas por tipo
Solar FV estimada    → #3B4CE8  (fill tozeroy rgba(59,76,232,0.10))
Eólica estimada      → #4DC8DC  (fill tozeroy rgba(77,200,220,0.12))
PCP programada       → #F59E0B  (línea dash, sin fill)
Gen real             → color primario de tecnología
Viento / GHI         → #6B7280  (dot, eje secundario y2)
```
```css
/* Wrapper CSS del gráfico */
border-radius: 12px; overflow: hidden;
box-shadow: 0 2px 10px rgba(0,0,0,0.06);
animation: fadeInUp 0.5s ease both;
transition: box-shadow 0.2s ease;
/* Hover */
box-shadow: 0 6px 20px rgba(59,76,232,0.12);
```

### Animaciones CSS (keyframes definidos en app_ernc.py)
```css
fadeInUp:     opacity 0→1, translateY 16px→0  — página, gráficos, tablas, cards
fadeInLeft:   opacity 0→1, translateX -12px→0 — cards de insights (escalonado)
pulse-border: box-shadow pulsante rojo         — insight crítico
dot-pulse:    scale 1→1.5→1                   — punto indicador en crítico
```
- Delay escalonado en insights: `animation-delay: idx * 0.06s`
- KPI cards con delay: `nth-child(n) { animation-delay: n*0.05s }`

### Cards de insights
```css
critico:  bg #FEF2F2, borde-izq #EF4444, badge rgba(239,68,68,0.12)
alerta:   bg #FFFBEB, borde-izq #F59E0B, badge rgba(245,158,11,0.12)
positivo: bg #F0FDF4, borde-izq #5AB848, badge rgba(90,184,72,0.10)
info:     bg #EFF6FF, borde-izq #3B4CE8, badge rgba(59,76,232,0.10)
border-radius: 0 10px 10px 0;  /* solo esquinas derechas redondeadas */
```

### Mapa pydeck
```css
border-radius: 14px; overflow: hidden;
box-shadow: 0 4px 16px rgba(0,0,0,0.12);
animation: fadeInUp 0.6s ease both;
```
- Estilo mapa: Carto Positron (light), NO Dark Matter
- Vista Chile completo: lat=-33.5, lon=-70.8, zoom=4.6
- Vista por parque: zoom=8.5, centrado en coordenadas del parque

### Tipografía
```
Título principal:  30px, 800, letter-spacing -0.5px, color #1A1F36
Subtítulos:        13px, 600, color #1A1F36
Texto secundario:  11-12px, 400/500, color #6B7280
Labels uppercase:  10-11px, 700, letter-spacing 0.8-1.2px
```

### Sidebar — sección fuentes de datos
Al final del sidebar, antes de la firma:
- Bloque con `background: rgba(255,255,255,0.07)`, borde sutil
- Título "FUENTES DE DATOS" en cyan 10px uppercase
- 4 filas: Gen. real CEN / PCP programada / Meteo Open-Meteo / CMG CEN S3
- Hora en formato `DD/MM HH:MM` — función `_fmt_hora(ts)` en `app_ernc.py`
- Query: `utils/db.query_ultimas_actualizaciones()` — devuelve dict con keys `gen_real`, `gen_prog`, `meteo`, `cmg`

### Firma al pie del sidebar
```html
<div style='border-top:1px solid rgba(255,255,255,0.12); text-align:center'>
  Dashboard creado por
  <b>Erick Herrera</b>
  AES Andes
</div>
```

---
