# -*- coding: utf-8 -*-
"""Dibujo SVG de las islas (componentes del grafo de transiciones) del paisaje de atractores."""
from collections import defaultdict


def _node_svg(P, x, cx, cy, cell, resaltar=False):
    """Mini cuadrícula centrada en (cx, cy). Devuelve (svg, ancho, alto)."""
    R = P.R
    m = R.m
    pad = 9
    w = h = (m - 1) * cell + 2 * pad if m > 1 else 2 * pad
    x0, y0 = cx - w / 2, cy - h / 2
    out = []
    if resaltar:
        out.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w}" height="{h}" rx="4" fill="#FFF7E0" stroke="#E0B84A"/>')

    def pos(i, j):
        return x0 + pad + j * cell, y0 + pad + i * cell
    for k in range(R.n):
        i, j = R.pos[k]
        for u in R.N[k]:
            if u > k:
                i2, j2 = R.pos[u]
                a, b = pos(i, j); c, d = pos(i2, j2)
                out.append(f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" stroke="#222" stroke-width="0.8"/>')
    fs = max(6, cell * 0.55)
    for k in range(R.n):
        i, j = R.pos[k]
        px, py = pos(i, j)
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{max(1.6, cell*0.16):.1f}" fill="#111"/>')
        dx = -3 if j == 0 else (3 if j == m - 1 else 2.5)
        dy = -2.5 if i == 0 else (fs + 1 if i == m - 1 else -2.5)
        anchor = "end" if j == 0 else "start"
        out.append(f'<text x="{px+dx:.1f}" y="{py+dy:.1f}" font-size="{fs:.0f}" font-weight="bold" fill="#B03A2E" text-anchor="{anchor}" font-family="sans-serif">{x[k]}</text>')
    return "".join(out), w, h


def island_svg(P, aid, max_hijos=None, max_nodos=None, cell=None):
    """Árbol de la isla del atractor aid. Con max_hijos / max_nodos se dibuja un bosquejo:
    a lo más max_hijos preimágenes por nodo y max_nodos nodos en total; se anota cuántas se omiten."""
    R = P.R
    m = R.m
    cell = cell or {1: 16, 2: 14, 3: 12, 4: 9}.get(m, 8)
    A = P.atractores[aid]
    miembros = P.cuenca[aid]
    hijos = defaultdict(list)
    for y in miembros:
        if P.altura[y] > 0:
            hijos[P.sig[y]].append(y)
    for k in hijos:
        hijos[k].sort(key=lambda z: (len(P.cuenca[aid]), z))
    omitidos = {}
    if max_hijos is not None or max_nodos is not None:
        # recorrido por anchura desde el atractor: se conservan a lo más max_hijos hijos por nodo
        # y a lo más max_nodos nodos en total; lo demás se anota como omitido
        todos = hijos
        hijos = defaultdict(list)
        cola = list(A); cuenta = len(A)
        while cola:
            k = cola.pop(0)
            hs = todos.get(k, [])
            for h in hs:
                if (max_hijos is not None and len(hijos[k]) >= max_hijos) or (max_nodos is not None and cuenta >= max_nodos):
                    break
                hijos[k].append(h); cuenta += 1; cola.append(h)
            if len(hijos[k]) < len(hs):
                omitidos[k] = len(hs) - len(hijos[k])
    pad = 9
    node_w = (m - 1) * cell + 2 * pad + 10 if m > 1 else 2 * pad + 10
    node_h = (m - 1) * cell + 2 * pad if m > 1 else 2 * pad
    unit = node_w + 6
    lvl = node_h + 30

    # ancho de subárbol en unidades de hoja
    anch = {}

    def ancho(x):
        if x in anch:
            return anch[x]
        hs = hijos.get(x, [])
        w = max(1, sum(ancho(h) for h in hs)) if hs else 1
        if x in omitidos:
            w += 1
        anch[x] = w
        return w
    total = sum(ancho(r) for r in A) + (1 if len(A) == 2 else 0)
    H = max(P.altura[y] for y in miembros)
    W_ = total * unit + 20
    Ht = (H + 1) * lvl + 30
    posn = {}
    out = []

    def colocar(x, left, nivel):
        w = ancho(x)
        cx = 10 + (left + w / 2) * unit
        cy = Ht - 20 - node_h / 2 - nivel * lvl
        posn[x] = (cx, cy)
        off = left
        for h in hijos.get(x, []):
            colocar(h, off, nivel + 1)
            off += ancho(h)
        if x in omitidos:
            ox = 10 + (off + 0.5) * unit
            oy = Ht - 20 - node_h / 2 - (nivel + 1) * lvl
            out.append(f'<text x="{ox:.1f}" y="{oy:.1f}" font-size="10" fill="#555" text-anchor="middle" font-family="sans-serif">+{omitidos[x]} más</text>')
            out.append(f'<line x1="{ox:.1f}" y1="{oy+8:.1f}" x2="{cx:.1f}" y2="{cy-node_h/2:.1f}" stroke="#999" stroke-width="0.8" stroke-dasharray="3,3"/>')
    left = 0
    for r in A:
        colocar(r, left, 0)
        left += ancho(r) + (1 if len(A) == 2 else 0)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_:.0f}" height="{Ht:.0f}" viewBox="0 0 {W_:.0f} {Ht:.0f}">',
           '<defs><marker id="ar" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#1F3A5F"/></marker></defs>',
           f'<rect x="0" y="0" width="{W_:.0f}" height="{Ht:.0f}" fill="#FFFFFF"/>']
    # flechas
    for y, (cx, cy) in posn.items():
        if P.altura[y] > 0 and P.sig[y] in posn:
            px, py = posn[P.sig[y]]
            svg.append(f'<line x1="{cx:.1f}" y1="{cy+node_h/2:.1f}" x2="{px:.1f}" y2="{py-node_h/2-2:.1f}" stroke="#1F3A5F" stroke-width="0.9" marker-end="url(#ar)"/>')
    if len(A) == 2:
        (x1, y1), (x2, y2) = posn[A[0]], posn[A[1]]
        svg.append(f'<text x="{(x1+x2)/2:.1f}" y="{y1+4:.1f}" font-size="14" fill="#1F3A5F" text-anchor="middle" font-family="sans-serif">⇄</text>')
    svg += out
    for y, (cx, cy) in posn.items():
        s, _, _ = _node_svg(P, y, cx, cy, cell, resaltar=(P.altura[y] == 0))
        svg.append(s)
    svg.append("</svg>")
    return "".join(svg), W_, Ht
