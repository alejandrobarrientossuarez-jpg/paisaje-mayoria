# -*- coding: utf-8 -*-
"""
app.py — Interfaz Streamlit para paisaje_mayoria.py
====================================================
Autómata de mayoría sobre rejillas cuadradas y su paisaje de atractores.

Ejecutar en local:   streamlit run app.py
Archivos necesarios: app.py, paisaje_mayoria.py, grafos.py, requirements.txt (misma carpeta)
"""

import math
from collections import Counter

import streamlit as st

from paisaje_mayoria import construir
from grafos import grafo_atractor_svg

st.set_page_config(page_title="Paisaje de atractores — autómata de mayoría", page_icon="🔲", layout="wide")


# ---------------------------------------------------------------------------
# Cálculo (en caché: cada rejilla se calcula una sola vez por sesión del servidor)
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Calculando el paisaje de atractores... (la rejilla 5×5 tarda alrededor de un minuto)")
def calcular(n: int):
    return construir(n, avisar=lambda s: None)


def df(data, height=None):
    """st.dataframe compatible con versiones nuevas (width='stretch') y antiguas (use_container_width)."""
    kw = {"height": height} if height else {}
    try:
        return st.dataframe(data, width="stretch", **kw)
    except TypeError:
        return st.dataframe(data, use_container_width=True, **kw)


# ---------------------------------------------------------------------------
# Dibujo de una configuración como cuadrícula (puntos + estado)
# ---------------------------------------------------------------------------

def svg_config(P, x, cell=34, resaltar=False):
    R = P.R
    m = R.m
    pad = 18
    w = h = (m - 1) * cell + 2 * pad if m > 1 else 2 * pad
    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    if resaltar:
        partes.append(f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="6" fill="#FFF7E0" stroke="#E0B84A"/>')

    def pos(i, j):
        return pad + j * cell, pad + i * cell
    for k in range(R.n):
        i, j = R.pos[k]
        for u in R.N[k]:
            if u > k:
                i2, j2 = R.pos[u]
                x1, y1 = pos(i, j); x2, y2 = pos(i2, j2)
                partes.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#222" stroke-width="1.2"/>')
    for k in range(R.n):
        i, j = R.pos[k]
        cx, cy = pos(i, j)
        partes.append(f'<circle cx="{cx}" cy="{cy}" r="3.2" fill="#111"/>')
        dx = -6 if j == 0 else (6 if j == m - 1 else 5)
        dy = -5 if i == 0 else (12 if i == m - 1 else -5)
        anchor = "end" if j == 0 else "start"
        partes.append(f'<text x="{cx+dx}" y="{cy+dy}" font-size="11" font-weight="bold" fill="#B03A2E" text-anchor="{anchor}" font-family="sans-serif">{x[k]}</text>')
    partes.append("</svg>")
    return "".join(partes)


def fila_de_configs(P, cfgs, etiquetas=None, por_fila=8, resaltar=False, cell=None):
    cell = cell or {1: 34, 2: 34, 3: 30, 4: 24, 5: 20}.get(P.R.m, 18)
    for k in range(0, len(cfgs), por_fila):
        cols = st.columns(por_fila)
        for c, (idx, x) in zip(cols, list(enumerate(cfgs))[k:k + por_fila]):
            with c:
                st.markdown(svg_config(P, x, cell=cell, resaltar=resaltar), unsafe_allow_html=True)
                st.caption(etiquetas[idx] if etiquetas else P.fmt.corto(x))


# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------

st.sidebar.title("Autómata de mayoría")
st.sidebar.markdown("Rejilla cuadrada m×m, espacio de configuraciones {0,1}ⁿ con n = m².")
opciones = ["{0,1}^1  (rejilla 1×1)", "{0,1}^4  (rejilla 2×2)", "{0,1}^9  (rejilla 3×3)", "{0,1}^16 (rejilla 4×4)", "{0,1}^25 (rejilla 5×5)"]
opcion = st.sidebar.selectbox("Espacio de configuraciones", opciones, index=1)
n = int(opcion.split("^")[1].split()[0])
if n == 25:
    st.sidebar.warning("La rejilla 5×5 tiene 33 554 432 configuraciones: necesita numpy, unos 2 GB de memoria libre y alrededor de un minuto la primera vez.")
try:
    P = calcular(n)
except ImportError:
    st.error("Para la rejilla 5×5 se necesita numpy: en la Anaconda Prompt ejecute  pip install numpy")
    st.stop()
except MemoryError:
    st.error("No hay memoria suficiente para la rejilla 5×5 en esta computadora.")
    st.stop()
fmt = P.fmt
R = P.R
m = R.m
grande = P.n_X > 65536          # rejilla 5×5: no se listan tablas gigantes

st.sidebar.markdown("---")
st.sidebar.markdown(f"**n = {R.n}**, |X| = 2^{R.n} = {P.n_X:,}")
st.sidebar.markdown(f"Atractores: **{len(P.atractores):,}**  \nPuntos fijos: **{len(P.fijos):,}**  \n2-ciclos: **{len(P.ciclos):,}**  \nProfundidad máxima: **{P.profundidad_max}**")
st.sidebar.markdown("---")
st.sidebar.caption("Regla: cada vértice adopta el estado mayoritario de sus vecinos; en empate conserva el suyo. Actualización síncrona. "
                   "Convenciones: 2×2 con vértices a, b, c, d en sentido horario; m ≥ 3 numerados por filas.")
if not grande:
    st.sidebar.download_button("Descargar reporte completo (.txt)", P.reporte(completo=True), file_name=f"paisaje_{m}x{m}.txt")
else:
    st.sidebar.download_button("Descargar reporte resumido (.txt)", P.reporte(completo=False), file_name=f"paisaje_{m}x{m}.txt")

# ---------------------------------------------------------------------------
# Contenido principal
# ---------------------------------------------------------------------------

st.title(f"Paisaje de atractores en la rejilla {m}×{m}")

tabs = st.tabs(["1 · La red", "2 · El autómata", "3 · Puntos fijos", "4 · Puntos periódicos", "5 · Atractores",
                "6 · Cuencas de atracción", "7 · Paisaje", "8 · Trayectoria"])

# ---- 1. Red ----
with tabs[0]:
    st.subheader("Grafo de cuadrícula")
    col1, col2 = st.columns([1, 2])
    with col1:
        cell, pad = 44, 22
        w = (m - 1) * cell + 2 * pad if m > 1 else 2 * pad
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{w}">']
        pos = lambda i, j: (pad + j * cell, pad + i * cell)
        for k in range(R.n):
            i, j = R.pos[k]
            for u in R.N[k]:
                if u > k:
                    i2, j2 = R.pos[u]
                    svg.append(f'<line x1="{pos(i,j)[0]}" y1="{pos(i,j)[1]}" x2="{pos(i2,j2)[0]}" y2="{pos(i2,j2)[1]}" stroke="#222" stroke-width="1.3"/>')
        for k in range(R.n):
            i, j = R.pos[k]
            cx, cy = pos(i, j)
            svg.append(f'<circle cx="{cx}" cy="{cy}" r="3.5" fill="#111"/>')
            dx = -7 if j == 0 else (7 if j == m - 1 else 6)
            dy = -6 if i == 0 else (14 if i == m - 1 else -6)
            svg.append(f'<text x="{cx+dx}" y="{cy+dy}" font-size="12" fill="#1F3A5F" text-anchor="{"end" if j == 0 else "start"}" font-family="sans-serif">{R.et(k)}</text>')
        svg.append("</svg>")
        st.markdown("".join(svg), unsafe_allow_html=True)
    with col2:
        st.markdown(f"**V** = {{{', '.join(R.etiquetas)}}}, |V| = {R.n}")
        st.markdown("**E** = {" + ", ".join("{%s,%s}" % (R.et(a), R.et(b)) for a, b in R.aristas) + "}, |E| = %d" % len(R.aristas))
        st.table([{"vértice": R.et(k), "vecindad N(v)": "{" + ", ".join(R.et(u) for u in sorted(R.N[k])) + "}",
                   "grado": R.deg[k], "tipo": R.tipo(k)} for k in range(R.n)])

# ---- 2. Autómata ----
with tabs[1]:
    st.subheader("Reglas locales y aplicación global")
    st.markdown(f"X = {{0,1}}^{R.n}, |X| = {P.n_X:,}. Regla de mayoría con empate → conserva.")
    for k in range(R.n):
        d = R.deg[k]
        vec = ", ".join(R.et(u) for u in sorted(R.N[k]))
        regla = {2: "copia a sus dos vecinos si coinciden; si difieren conserva",
                 3: "toma el valor mayoritario de sus tres vecinos",
                 4: "1 si ≥3 vecinos en 1; 0 si ≤1; conserva si exactamente 2",
                 1: "copia a su único vecino", 0: "sin vecinos: conserva"}[d]
        st.markdown(f"- **{R.et(k)}′** = f({vec}) : {regla}")
    if P.n_X <= 512:
        st.markdown("**Tabla completa de F_G**")
        df([{"x": fmt.corto(x), "F(x)": fmt.corto(P.sig_de(x)), "¿fijo?": "sí" if P.sig_de(x) == x else "no",
             "profundidad τ": P.profundidad_de(x), "atractor": f"A{P.atractor_de(x) + 1}"} for x in P.todas()], height=420)
    else:
        st.info(f"La tabla completa tiene {P.n_X:,} renglones; consúltela con la pestaña Trayectoria o descargue el reporte.")

# ---- 3. Fijos ----
with tabs[2]:
    st.subheader(f"Fix(G) = {{ x : F(x) = x }}  —  |Fix(G)| = {len(P.fijos):,}")
    st.caption("Criterio: ningún vértice tiene más vecinos contrarios que deg(v)/2.")
    if len(P.fijos) <= 120:
        fila_de_configs(P, P.fijos, etiquetas=[f"{fmt.corto(x)} · cuenca {P.tam_cuenca(P.atractor_de(x)):,}" for x in P.fijos])
    else:
        k_ = st.slider("Dibujar los primeros", 8, min(len(P.fijos), 400), 40, step=8, key="sl_fijos")
        fila_de_configs(P, P.fijos[:k_], etiquetas=[f"{fmt.corto(x)} · cuenca {P.tam_cuenca(P.atractor_de(x)):,}" for x in P.fijos[:k_]])
    df([{"#": i + 1, "punto fijo": fmt.largo(x), "tamaño de cuenca": P.tam_cuenca(P.atractor_de(x))} for i, x in enumerate(P.fijos)], height=400)
    if len(P.fijos) <= 500:
        st.markdown("Fix(G) = { " + ", ".join(fmt.vector(x) for x in P.fijos) + " }")

# ---- 4. Periódicos ----
with tabs[3]:
    por_p = Counter(p for _, p in P.periodicos)
    st.subheader(f"Per(G)  —  |Per(G)| = {len(P.periodicos):,}   (" + ", ".join(f"período {p}: {c:,}" for p, c in sorted(por_p.items())) + ")")
    st.caption(f"Puntos transitorios (no periódicos): {P.n_X - len(P.periodicos):,}. Por el teorema de Goles–Olivos sólo hay períodos 1 y 2.")
    df([{"configuración": fmt.largo(x), "período": p,
         "órbita periódica O(x)": " ⇄ ".join(fmt.corto(c) for c in P.atractores[P.atractor_de(x)])} for x, p in P.periodicos], height=400)
    if P.ciclos:
        st.markdown("**Ciclos de longitud 2 (x ⇄ F(x))**")
        k_ = len(P.ciclos) if len(P.ciclos) <= 60 else st.slider("Dibujar los primeros", 8, min(len(P.ciclos), 400), 40, step=8, key="sl_cic")
        for k in range(0, k_, 4):
            cols = st.columns(4)
            for c, A in zip(cols, P.ciclos[k:k + 4]):
                with c:
                    st.markdown(svg_config(P, A[0], cell=22) + '<span style="font-size:18px;vertical-align:60%;">&nbsp;⇄&nbsp;</span>' + svg_config(P, A[1], cell=22), unsafe_allow_html=True)
                    st.caption(f"{fmt.corto(A[0])} ⇄ {fmt.corto(A[1])} · cuenca {P.tam_cuenca(P.atractor_de(A[0])):,}")

# ---- 5. Atractores ----
with tabs[4]:
    st.subheader(f"Att(G)  —  |Att(G)| = {len(P.atractores):,}   ({len(P.fijos):,} puntos fijos, {len(P.ciclos):,} ciclos de longitud 2)")
    df([{"atractor": f"A{i + 1}", "configuraciones": " ⇄ ".join(fmt.corto(c) for c in A), "período": len(A),
         "|B(A)|": P.tam_cuenca(i), "profundidad máx. en la cuenca": len(P.niveles(i)) - 1} for i, A in enumerate(P.atractores)] if not grande else
       [{"atractor": f"A{i + 1}", "configuraciones": " ⇄ ".join(fmt.corto(c) for c in A), "período": len(A), "|B(A)|": P.tam_cuenca(i)} for i, A in enumerate(P.atractores)],
       height=420)
    if len(P.atractores) <= 500:
        st.markdown("**Att(G) en nomenclatura completa:**")
        st.code("Att(G) = { " + ", ".join("{" + ", ".join(fmt.vector(c) for c in A) + "}" for A in P.atractores) + " }", language=None)

# ---- 6. Cuencas ----
with tabs[5]:
    tam = [P.tam_cuenca(i) for i in range(len(P.atractores))]
    st.subheader("Cuencas de atracción B(A) = { x : F^t(x) ∈ A para algún t }")
    st.markdown(f"Suma de los tamaños de las {len(tam):,} cuencas = {sum(tam):,} = |X| ✓ (las cuencas forman una partición de X)")
    if len(P.atractores) <= 500:
        st.markdown("Tamaños: " + ", ".join(f"|B(A{i + 1})| = {t:,}" for i, t in enumerate(tam)))
        sel = st.selectbox("Elija un atractor", [f"A{i + 1}: " + " ⇄ ".join(fmt.corto(c) for c in A) + f"  (|B| = {tam[i]:,})" for i, A in enumerate(P.atractores)])
        i = int(sel.split(":")[0][1:]) - 1
    else:
        i = int(st.number_input(f"Número del atractor (1 a {len(P.atractores):,})", min_value=1, max_value=len(P.atractores), value=1, step=1)) - 1
    niv = P.niveles(i)
    st.markdown(f"**B(A{i + 1})**, atractor {{ {' ⇄ '.join(fmt.corto(c) for c in P.atractores[i])} }}: {tam[i]:,} configuraciones. Niveles: " +
                ", ".join(f"L{k} = {v:,}" for k, v in enumerate(niv)))
    st.markdown("**Atractor:**")
    fila_de_configs(P, list(P.atractores[i]), resaltar=True)
    lim = st.slider("Configuraciones a mostrar", min_value=min(10, tam[i]), max_value=min(tam[i], 2000), value=min(60, tam[i]), key="sl_cu") if tam[i] > 10 else tam[i]
    miembros = P.miembros(i, lim)
    df([{"τ (profundidad)": P.profundidad_de(x), "x": fmt.corto(x), "F(x)": fmt.corto(P.sig_de(x)) if P.profundidad_de(x) > 0 else "(en el atractor)"} for x in miembros], height=380)
    if tam[i] <= 48:
        st.markdown("**Todas las configuraciones de la cuenca, por profundidad:**")
        for k, v in enumerate(niv):
            st.markdown(f"Profundidad {k} ({v}):")
            fila_de_configs(P, [x for x in miembros if P.profundidad_de(x) == k], resaltar=(k == 0))

# ---- 7. Paisaje ----
with tabs[6]:
    B0, B1 = P.tam_cuenca(P.id_cero), P.tam_cuenca(P.id_uno)
    st.subheader("L(G) = { (A, B(A)) : A ∈ Att(G) }")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Atractores", f"{len(P.atractores):,}"); c2.metric("Puntos periódicos", f"{len(P.periodicos):,}")
    c3.metric("Profundidad máxima", P.profundidad_max); c4.metric("Jardines del Edén", f"{P.n_eden:,} ({100 * P.n_eden / P.n_X:.1f} %)")
    c1.metric("|B0| = |B1|", f"{B0:,}"); c2.metric("|B_sync|", f"{B0 + B1:,}"); c3.metric("Sincroniza", f"{100 * (B0 + B1) / P.n_X:.2f} %")
    c4.metric("Globalmente sincronizante", "Sí" if B0 + B1 == P.n_X else "No")
    st.markdown("**Configuraciones por profundidad τ:** " + ", ".join(f"τ = {k}: {v:,}" for k, v in enumerate(P.histograma_profundidad())))
    st.markdown("**Niveles de B0:** " + ", ".join(f"L{k} = {v:,}" for k, v in enumerate(P.niveles(P.id_cero))))

    st.markdown("---")
    st.markdown("## Los grafos del paisaje: cada atractor con su cuenca")
    st.markdown("El grafo de transiciones Γ_G tiene una flecha x → F_G(x) por configuración y se separa en un componente por atractor: "
                "el componente de A es su cuenca B(A). En cada dibujo, abajo y en amarillo está el atractor (⇄ si es un 2-ciclo); "
                "cada nivel hacia arriba son las configuraciones de profundidad 1, 2, …; cada flecha es x → F_G(x). Los dibujos anchos se desplazan horizontalmente.")
    total = len(P.atractores)
    LIM_COMPLETO = 300
    LIM_ABSOLUTO = 3000
    colA, colB, colC = st.columns([1, 1, 1])
    orden = colA.radio("Orden de los atractores", ["por número (A1, A2, …)", "por tamaño de cuenca (mayor a menor)"], index=0)
    idxs = list(range(total))
    if orden.startswith("por tamaño"):
        idxs.sort(key=lambda i: (-P.tam_cuenca(i), i))
    por_pagina = colB.selectbox("Atractores por página", [10, 20, 40, 80, total] if total <= 500 else [10, 20, 40, 80], index=(1 if total > 20 else 4 if total <= 500 else 1)) if total > 10 else total
    n_pag = max(1, math.ceil(total / por_pagina))
    pag = colC.number_input("Página", min_value=1, max_value=n_pag, value=1, step=1) if n_pag > 1 else 1
    completo = st.checkbox(f"Dibujar completas también las cuencas grandes (entre {LIM_COMPLETO} y {LIM_ABSOLUTO} configuraciones); puede tardar y ser muy ancho", value=False)
    bosquejo_hijos = 3
    for i in idxs[(pag - 1) * por_pagina: pag * por_pagina]:
        A = P.atractores[i]
        t_ = P.tam_cuenca(i)
        niv = P.niveles(i)
        st.markdown(f"#### Atractor A{i + 1} = {{ {' ⇄ '.join(fmt.corto(c) for c in A)} }}  ·  período {len(A)}  ·  cuenca de {t_:,} configuraciones  ·  "
                    + ", ".join(f"L{k}={v:,}" for k, v in enumerate(niv)))
        if t_ > LIM_COMPLETO and not (completo and t_ <= LIM_ABSOLUTO):
            svg, w, h = grafo_atractor_svg(P, i, max_hijos=bosquejo_hijos, max_nodos=80)
            st.caption(f"Bosquejo: se muestran a lo más {bosquejo_hijos} preimágenes por configuración y 80 configuraciones en total; '+n más' indica las omitidas."
                       + (" Active la casilla de arriba para el dibujo completo." if t_ <= LIM_ABSOLUTO else f" Esta cuenca supera las {LIM_ABSOLUTO:,} configuraciones y sólo se dibuja como bosquejo."))
        else:
            svg, w, h = grafo_atractor_svg(P, i)
        st.markdown(f'<div style="overflow-x:auto; border:1px solid #ddd; border-radius:6px; padding:4px; margin-bottom:12px;">{svg}</div>', unsafe_allow_html=True)
    st.markdown("---")
    tam_all = [P.tam_cuenca(i) for i in range(total)]
    st.bar_chart({"cuenca": {f"A{i + 1}": tam_all[i] for i in range(total)}} if total <= 60 else {"tamaños de cuenca (ordenados)": sorted(tam_all, reverse=True)})
    if not grande:
        df([{"atractor": f"A{i + 1}", "configuraciones": " ⇄ ".join(fmt.corto(c) for c in A), "período": len(A),
             "|B(A)|": tam_all[i], "profundidad máx.": len(P.niveles(i)) - 1,
             "niveles": ", ".join(f"L{k}={v}" for k, v in enumerate(P.niveles(i)))} for i, A in enumerate(P.atractores)], height=380)
    else:
        df([{"atractor": f"A{i + 1}", "configuraciones": " ⇄ ".join(fmt.corto(c) for c in A), "período": len(A), "|B(A)|": tam_all[i]} for i, A in enumerate(P.atractores)], height=380)
    if P.n_eden <= 64:
        st.markdown("**Jardines del Edén:** " + ", ".join(fmt.corto(x) for x in P.eden_lista(64)))

# ---- 8. Trayectoria ----
with tabs[7]:
    st.subheader("Trayectoria de una configuración")
    ejemplo = {1: "0", 2: "(1,0,1,0)", 3: "000/011/010", 4: "0000/0110/0011/1100", 5: "00000/01100/00110/11000/00000"}[m]
    s = st.text_input("Escriba la configuración (como vector o por filas)", value=ejemplo)
    try:
        x = fmt.leer(s)
        tr, _ = P.trayectoria(x)
        h = P.profundidad_de(x)
        fila_de_configs(P, tr, etiquetas=[f"t = {t}" + ("  (atractor)" if h <= t else "") for t in range(len(tr))])
        st.text(P.s_trayectoria(x))
    except ValueError as e:
        st.error(f"Formato no válido: {e}")
