#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paisaje_mayoria.py
==================
Autómata de mayoría sobre rejillas cuadradas m×m (n = m² vértices, espacio de
configuraciones {0,1}^n) y cálculo completo de su PAISAJE DE ATRACTORES.

Calcula y enlista:
  * la red (vértices, aristas, vecindades, grados),
  * la aplicación global F_G (tabla completa si n es pequeño),
  * los puntos fijos  Fix(G),
  * los puntos periódicos con su período  Per(G),
  * los atractores  Att(G)  (órbitas periódicas),
  * las cuencas de atracción  B(A)  con sus niveles (alturas),
  * el paisaje L(G): tamaños, profundidad, Jardines del Edén, cuencas de
    sincronización B0, B1, B_sync y fracción sincronizante,
  * la trayectoria de cualquier configuración que el usuario escriba.

Valores de n previstos: 1, 4, 9, 16 (rejillas 1×1, 2×2, 3×3, 4×4).
También acepta 25 (5×5, 33 554 432 configuraciones) en modo "resumen"
si numpy está instalado y hay ~2 GB de memoria libre.

Convenciones (las mismas de los documentos):
  * 2×2: vértices a, b, c, d en sentido horario (a arriba-izq, b arriba-der,
         c abajo-der, d abajo-izq). Vector x = (a, b, c, d).
  * m ≥ 3: vértices numerados por filas 1, 2, ..., n. Vector x = (x1, ..., xn),
         escrito también por filas, p. ej. 000/011/010.
  * Regla de mayoría: un vértice adopta el estado mayoritario de sus vecinos;
    en empate conserva su estado. Actualización síncrona.

Uso:  python3 paisaje_mayoria.py            (menú interactivo)
      python3 paisaje_mayoria.py 9          (calcula la rejilla 3×3 y abre el menú)
      python3 paisaje_mayoria.py 9 --todo   (imprime todo y guarda el reporte)
"""

import sys
import math
import itertools
from collections import Counter, defaultdict

# ---------------------------------------------------------------------------
# 1. LA RED
# ---------------------------------------------------------------------------

class Rejilla:
    """Grafo de cuadrícula m×m con la convención de etiquetado de los documentos."""

    def __init__(self, m):
        if m < 1:
            raise ValueError("m debe ser ≥ 1")
        self.m = m
        self.n = m * m
        # posición (fila i, columna j) de cada índice 0..n-1
        if m == 2:
            # a, b, c, d en sentido horario
            self.etiquetas = ["a", "b", "c", "d"]
            self.pos = {0: (0, 0), 1: (0, 1), 2: (1, 1), 3: (1, 0)}
        else:
            self.etiquetas = [str(k + 1) for k in range(self.n)]
            self.pos = {k: (k // m, k % m) for k in range(self.n)}
        self.idx_de_pos = {p: k for k, p in self.pos.items()}
        # vecindades
        self.N = {}
        for k, (i, j) in self.pos.items():
            vec = []
            for (a, b) in [(i - 1, j), (i, j - 1), (i, j + 1), (i + 1, j)]:
                if (a, b) in self.idx_de_pos:
                    vec.append(self.idx_de_pos[(a, b)])
            self.N[k] = vec
        self.deg = {k: len(v) for k, v in self.N.items()}
        self.aristas = sorted({tuple(sorted((k, u))) for k in self.N for u in self.N[k]})

    def et(self, k):
        return self.etiquetas[k]

    def tipo(self, k):
        d = self.deg[k]
        return {0: "aislado", 1: "extremo", 2: "esquina", 3: "borde", 4: "interior"}[d]

    def describir(self):
        m = self.m
        out = []
        out.append(f"Rejilla {m}×{m}: n = {self.n} vértices, {len(self.aristas)} aristas.")
        if m == 2:
            out.append("Etiquetado horario: a (arriba-izq), b (arriba-der), c (abajo-der), d (abajo-izq).")
        elif m >= 3:
            out.append("Etiquetado por filas: 1..%d en la fila 1, ..., hasta %d." % (m, self.n))
        out.append("V = {" + ", ".join(self.etiquetas) + "}")
        out.append("E = {" + ", ".join("{%s,%s}" % (self.et(a), self.et(b)) for a, b in self.aristas) + "}")
        out.append("")
        out.append("  vértice   vecindad N(v)        grado   tipo")
        for k in range(self.n):
            vec = "{" + ", ".join(self.et(u) for u in sorted(self.N[k])) + "}"
            out.append(f"  {self.et(k):>7}   {vec:<20} {self.deg[k]:>5}   {self.tipo(k)}")
        out.append("")
        out.append("Dibujo (posiciones):")
        for i in range(m):
            out.append("   " + "  ".join(f"{self.et(self.idx_de_pos[(i, j)]):>2}" for j in range(m)))
        return "\n".join(out)


# ---------------------------------------------------------------------------
# 2. EL AUTÓMATA: regla local y aplicación global
# ---------------------------------------------------------------------------

def regla_local(x, k, N):
    """Estado siguiente del vértice k dada la configuración x (tupla)."""
    vec = N[k]
    d = len(vec)
    n1 = sum(x[u] for u in vec)
    if 2 * n1 > d:
        return 1
    if 2 * n1 < d:
        return 0
    return x[k]                      # empate: conserva


def F(x, N):
    """Aplicación global F_G: aplica la regla local a todos los vértices a la vez."""
    return tuple(regla_local(x, k, N) for k in range(len(x)))


# ---------------------------------------------------------------------------
# 3. FORMATO DE CONFIGURACIONES
# ---------------------------------------------------------------------------

class Formato:
    def __init__(self, R):
        self.R = R

    def vector(self, x):
        return "(" + ",".join(str(v) for v in x) + ")"

    def filas(self, x):
        """Escritura por filas (fila 1 / fila 2 / ...), usando las posiciones reales."""
        m = self.R.m
        filas = []
        for i in range(m):
            filas.append("".join(str(x[self.R.idx_de_pos[(i, j)]]) for j in range(m)))
        return "/".join(filas)

    def corto(self, x):
        return self.vector(x) if self.R.m <= 2 else self.filas(x)

    def largo(self, x):
        if self.R.m <= 2:
            return self.vector(x)
        return f"{self.filas(x)}  {self.vector(x)}"

    def leer(self, s):
        """Lee una configuración escrita como vector '(1,0,0,1)', '1001' o por filas '000/011/010'."""
        s = s.strip().replace(" ", "")
        n, m = self.R.n, self.R.m
        if "/" in s:
            partes = s.split("/")
            if len(partes) != m or any(len(p) != m for p in partes):
                raise ValueError("se esperaban %d filas de %d dígitos" % (m, m))
            x = [0] * n
            for i, p in enumerate(partes):
                for j, ch in enumerate(p):
                    x[self.R.idx_de_pos[(i, j)]] = int(ch)
            return tuple(x)
        s = s.strip("()[]").replace(",", "")
        if len(s) != n or any(ch not in "01" for ch in s):
            raise ValueError("se esperaban %d dígitos 0/1" % n)
        return tuple(int(ch) for ch in s)


# ---------------------------------------------------------------------------
# 4. EL PAISAJE DE ATRACTORES (motor exacto, n ≤ 16)
# ---------------------------------------------------------------------------

class Paisaje:
    """Calcula todo el paisaje de atractores por enumeración exhaustiva."""

    def __init__(self, R):
        self.R = R
        self.fmt = Formato(R)
        n = R.n
        self.X = list(itertools.product((0, 1), repeat=n))
        self.sig = {x: F(x, R.N) for x in self.X}          # tabla x -> F(x)
        self._clasificar()

    # ---- clasificación en atractores, alturas, cuencas ----
    def _clasificar(self):
        sig = self.sig
        self.atractor_de = {}      # x -> índice del atractor
        self.altura = {}           # x -> τ(x)
        self.atractores = []       # lista de tuplas (ciclos)
        for x in self.X:
            if x in self.atractor_de:
                continue
            camino, visto, y = [], {}, x
            while y not in self.atractor_de and y not in visto:
                visto[y] = len(camino)
                camino.append(y)
                y = sig[y]
            if y in self.atractor_de:                      # cayó en algo ya clasificado
                aid, h = self.atractor_de[y], self.altura[y]
                for z in reversed(camino):
                    h += 1
                    self.atractor_de[z], self.altura[z] = aid, h
            else:                                          # se cerró un ciclo nuevo
                k = visto[y]
                ciclo = camino[k:]
                aid = len(self.atractores)
                self.atractores.append(tuple(ciclo))
                for z in ciclo:
                    self.atractor_de[z], self.altura[z] = aid, 0
                h = 0
                for z in reversed(camino[:k]):
                    h += 1
                    self.atractor_de[z], self.altura[z] = aid, h
        # ordenar atractores: 0, 1, luego fijos por número de unos, luego ciclos por tamaño de cuenca
        cuenca_tam = Counter(self.atractor_de.values())
        n = self.R.n
        cero, uno = tuple([0] * n), tuple([1] * n)

        def clave(aid):
            A = self.atractores[aid]
            if A == (cero,):
                return (0, 0, 0)
            if A == (uno,):
                return (0, 1, 0)
            return (len(A), -cuenca_tam[aid], A)
        orden = sorted(range(len(self.atractores)), key=clave)
        nuevo = {old: new for new, old in enumerate(orden)}
        self.atractores = [self.atractores[o] for o in orden]
        self.atractor_de = {x: nuevo[a] for x, a in self.atractor_de.items()}
        # miembros de cada cuenca
        self.cuenca = defaultdict(list)
        for x in self.X:
            self.cuenca[self.atractor_de[x]].append(x)
        for aid in self.cuenca:
            self.cuenca[aid].sort(key=lambda z: (self.altura[z], self.fmt.corto(self.sig[z]), z))
        # derivados
        self.fijos = [A[0] for A in self.atractores if len(A) == 1]
        self.ciclos = [A for A in self.atractores if len(A) >= 2]
        self.periodicos = [(x, len(self.atractores[self.atractor_de[x]])) for x in self.X if self.altura[x] == 0]
        self.profundidad = max(self.altura.values())
        self.imagenes = set(self.sig.values())
        self.eden = [x for x in self.X if x not in self.imagenes]
        self.id_cero = self.atractor_de[cero]
        self.id_uno = self.atractor_de[uno]

    # ---- utilidades ----
    def periodo(self, x):
        return len(self.atractores[self.atractor_de[x]]) if self.altura[x] == 0 else None

    def trayectoria(self, x):
        tr = [x]
        vistos = {x}
        y = self.sig[x]
        while y not in vistos:
            tr.append(y)
            vistos.add(y)
            y = self.sig[y]
        return tr, y     # y = primera repetición

    def niveles(self, aid):
        c = Counter(self.altura[x] for x in self.cuenca[aid])
        return [c[k] for k in range(max(c) + 1)]

    # ---- secciones de texto ----
    def s_red(self):
        return "1. LA RED\n" + "=" * 60 + "\n" + self.R.describir()

    def s_automata(self, tabla_max=64):
        R, fmt = self.R, self.fmt
        out = ["2. EL AUTÓMATA DE MAYORÍA", "=" * 60]
        out.append(f"Espacio de configuraciones X = {{0,1}}^{R.n}, |X| = 2^{R.n} = {len(self.X)}.")
        out.append("Regla local (empate → conserva), escrita por vértice:")
        for k in range(R.n):
            vec = ", ".join(R.et(u) for u in sorted(R.N[k]))
            d = R.deg[k]
            if d == 2:
                regla = "copia a sus dos vecinos si coinciden; si difieren conserva su estado"
            elif d == 3:
                regla = "toma el valor mayoritario de sus tres vecinos (sin empates)"
            elif d == 4:
                regla = "1 si ≥3 vecinos en 1; 0 si ≤1; conserva si exactamente 2"
            elif d == 1:
                regla = "copia a su único vecino"
            else:
                regla = "sin vecinos: conserva"
            out.append(f"   {R.et(k)}' = f_{R.et(k)}({vec}) : {regla}")
        if len(self.X) <= tabla_max:
            out.append("")
            out.append("Tabla completa de F_G (x → F_G(x)):")
            for x in self.X:
                y = self.sig[x]
                marca = "  ← punto fijo" if y == x else ""
                out.append(f"   {fmt.corto(x)} → {fmt.corto(y)}{marca}")
        else:
            out.append(f"(La tabla completa tiene {len(self.X)} renglones; use la opción 'trayectoria' para consultar configuraciones concretas.)")
        return "\n".join(out)

    def s_fijos(self):
        fmt = self.fmt
        out = ["3. PUNTOS FIJOS  Fix(G) = { x : F_G(x) = x }", "=" * 60]
        out.append(f"|Fix(G)| = {len(self.fijos)}")
        for i, x in enumerate(self.fijos, 1):
            out.append(f"   {i:>3}. {fmt.largo(x)}   cuenca de tamaño {len(self.cuenca[self.atractor_de[x]])}")
        out.append("Criterio de verificación: ningún vértice tiene más vecinos contrarios que deg(v)/2.")
        return "\n".join(out)

    def s_periodicos(self):
        fmt = self.fmt
        out = ["4. PUNTOS PERIÓDICOS  Per(G) = { x : F_G^p(x) = x para algún p ≥ 1 }", "=" * 60]
        por_periodo = Counter(p for _, p in self.periodicos)
        out.append(f"|Per(G)| = {len(self.periodicos)}   " + ", ".join(f"período {p}: {c}" for p, c in sorted(por_periodo.items())))
        out.append(f"Puntos transitorios: |X \\ Per(G)| = {len(self.X) - len(self.periodicos)}")
        out.append("")
        out.append("   configuración                      período   órbita periódica O(x)")
        for x, p in self.periodicos:
            A = self.atractores[self.atractor_de[x]]
            orbita = " ⇄ ".join(fmt.corto(c) for c in A) if p > 1 else "{" + fmt.corto(x) + "}"
            out.append(f"   {fmt.largo(x):<34} {p:>5}     {orbita}")
        return "\n".join(out)

    def s_atractores(self):
        fmt = self.fmt
        out = ["5. ATRACTORES  Att(G) (órbitas periódicas)", "=" * 60]
        out.append(f"|Att(G)| = {len(self.atractores)}   ({len(self.fijos)} puntos fijos, {len(self.ciclos)} ciclos de longitud 2)")
        for i, A in enumerate(self.atractores, 1):
            miembros = ", ".join(fmt.corto(c) for c in A)
            out.append(f"   A{i:<3} = {{ {miembros} }}   período {len(A)}   |B(A{i})| = {len(self.cuenca[i - 1])}")
        out.append("Att(G) = { " + ", ".join("{" + ", ".join(fmt.corto(c) for c in A) + "}" for A in self.atractores) + " }")
        return "\n".join(out)

    def s_cuencas(self, max_por_cuenca=None):
        fmt = self.fmt
        out = ["6. CUENCAS DE ATRACCIÓN  B(A) = { x : F_G^t(x) ∈ A para algún t }", "=" * 60]
        tam = [len(self.cuenca[i]) for i in range(len(self.atractores))]
        out.append("Tamaños: " + ", ".join(f"|B(A{i + 1})|={t}" for i, t in enumerate(tam)))
        out.append(f"Verificación de partición: suma = {sum(tam)} = |X| ✓" if sum(tam) == len(self.X) else "ERROR en la partición")
        for i, A in enumerate(self.atractores):
            miembros = self.cuenca[i]
            niv = self.niveles(i)
            out.append("")
            out.append(f"B(A{i + 1}), atractor {{ {', '.join(fmt.corto(c) for c in A)} }}: {len(miembros)} configuraciones; "
                       "niveles " + ", ".join(f"L{k}={v}" for k, v in enumerate(niv)))
            lista = miembros if max_por_cuenca is None else miembros[:max_por_cuenca]
            for x in lista:
                h = self.altura[x]
                flecha = "(en el atractor)" if h == 0 else f"→ {fmt.corto(self.sig[x])}"
                out.append(f"      τ={h:<2} {fmt.corto(x):<24} {flecha}")
            if max_por_cuenca is not None and len(miembros) > max_por_cuenca:
                out.append(f"      ... ({len(miembros) - max_por_cuenca} configuraciones más; use el reporte completo)")
        return "\n".join(out)

    def s_paisaje(self):
        fmt = self.fmt
        n = self.R.n
        B0, B1 = len(self.cuenca[self.id_cero]), len(self.cuenca[self.id_uno])
        out = ["7. PAISAJE DE ATRACTORES  L(G) = { (A, B(A)) : A ∈ Att(G) }", "=" * 60]
        out.append(f"|X| = {len(self.X)}")
        out.append(f"Atractores: {len(self.atractores)}  (fijos: {len(self.fijos)}, 2-ciclos: {len(self.ciclos)})")
        out.append(f"Puntos periódicos: {len(self.periodicos)}   transitorios: {len(self.X) - len(self.periodicos)}")
        out.append(f"Profundidad (altura máxima): {self.profundidad}")
        alt = Counter(self.altura.values())
        out.append("Configuraciones por altura: " + ", ".join(f"τ={k}: {alt[k]}" for k in sorted(alt)))
        out.append(f"Jardines del Edén (sin preimagen): {len(self.eden)}  ({100 * len(self.eden) / len(self.X):.2f} %)")
        out.append(f"|B0| = {B0}, |B1| = {B1}, |B_sync| = {B0 + B1}  ({100 * (B0 + B1) / len(self.X):.2f} % de X)")
        out.append("Niveles de B0: " + ", ".join(f"L{k}={v}" for k, v in enumerate(self.niveles(self.id_cero))))
        out.append("Globalmente sincronizante: " + ("SÍ" if B0 + B1 == len(self.X) else "NO"))
        out.append("")
        out.append("   atractor                                   período   |B(A)|   altura máx.")
        for i, A in enumerate(self.atractores):
            niv = self.niveles(i)
            out.append(f"   A{i + 1:<3} {' ⇄ '.join(fmt.corto(c) for c in A):<38} {len(A):>5}   {len(self.cuenca[i]):>6}   {len(niv) - 1:>5}")
        if len(self.eden) <= 64:
            out.append("")
            out.append("Jardines del Edén: " + ", ".join(fmt.corto(x) for x in self.eden))
        return "\n".join(out)

    def s_trayectoria(self, x):
        fmt = self.fmt
        tr, rep = self.trayectoria(x)
        aid = self.atractor_de[x]
        A = self.atractores[aid]
        out = [f"Trayectoria de {fmt.largo(x)}:"]
        for t, y in enumerate(tr):
            out.append(f"   t={t:<3} {fmt.corto(y)}" + ("   (entra al atractor)" if t == self.altura[x] and self.altura[x] > 0 else ""))
        out.append(f"Altura τ(x) = {self.altura[x]};  atractor A{aid + 1} = {{ {', '.join(fmt.corto(c) for c in A)} }} (período {len(A)});  |B(A{aid + 1})| = {len(self.cuenca[aid])}")
        p = self.periodo(x)
        out.append("Es punto periódico de período %d." % p if p else "Es punto transitorio (no periódico).")
        out.append("Es punto fijo." if self.sig[x] == x else "No es punto fijo.")
        out.append("Es Jardín del Edén (sin preimagen)." if x in self.eden else f"Tiene {sum(1 for z in self.X if self.sig[z] == x)} preimagen(es).")
        n = self.R.n
        if aid == self.id_cero or aid == self.id_uno:
            out.append(f"Sincroniza: T_sync = {self.altura[x]}.")
        else:
            out.append("No sincroniza (no cae en 0 ni en 1).")
        return "\n".join(out)

    def reporte(self, completo=True):
        partes = [self.s_red(), self.s_automata(tabla_max=(len(self.X) if completo else 64)), self.s_fijos(),
                  self.s_periodicos(), self.s_atractores(), self.s_cuencas(None if completo else 12), self.s_paisaje()]
        return "\n\n".join(partes)


# ---------------------------------------------------------------------------
# 5. MOTOR NUMPY PARA n = 25 (sólo resumen)
# ---------------------------------------------------------------------------

def resumen_numpy(m):
    import numpy as np
    n = m * m
    R = Rejilla(m)
    size = 1 << n
    idx = np.arange(size, dtype=np.uint32)
    sig = np.zeros(size, dtype=np.uint32)
    for v in range(n):
        s = np.zeros(size, dtype=np.uint8)
        for u in R.N[v]:
            s += ((idx >> np.uint32(u)) & np.uint32(1)).astype(np.uint8)
        d = len(R.N[v])
        propio = ((idx >> np.uint32(v)) & np.uint32(1)).astype(np.uint8)
        bit = ((2 * s.astype(np.int16) > d) | ((2 * s.astype(np.int16) == d) & (propio == 1))).astype(np.uint32)
        sig |= (bit << np.uint32(v))
        del s, propio, bit
    per = (sig[sig] == idx)
    fijos = int((sig == idx).sum()); periodicos = int(per.sum()); ciclos = (periodicos - fijos) // 2
    cur = idx.copy(); h = np.zeros(size, dtype=np.uint8)
    act = np.flatnonzero(~per[cur])
    while act.size:
        cur[act] = sig[cur[act]]
        h[act] += 1
        act = act[~per[cur[act]]]
    rep = np.minimum(cur, sig[cur])
    B0 = int((rep == 0).sum())
    u, c = np.unique(rep, return_counts=True)
    eden = size - np.unique(sig).size
    out = [f"RESUMEN DEL PAISAJE {m}×{m} (motor vectorizado)", "=" * 60,
           f"|X| = {size:,}", f"Atractores: {u.size:,} (fijos {fijos:,}, 2-ciclos {ciclos:,})",
           f"Puntos periódicos: {periodicos:,}", f"Profundidad: {int(h.max())}",
           f"|B0| = |B1| = {B0:,}, |B_sync| = {2 * B0:,} ({100 * 2 * B0 / size:.2f} %)",
           f"Jardines del Edén: {eden:,} ({100 * eden / size:.2f} %)",
           "Niveles de B0: " + ", ".join(f"L{k}={v:,}" for k, v in enumerate(np.bincount(h[rep == 0]).tolist())),
           "Mayores cuencas: " + ", ".join(f"{v:,}" for v in sorted(c.tolist(), reverse=True)[:10])]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 6. INTERFAZ
# ---------------------------------------------------------------------------

def elegir_n(arg=None):
    validos = {1: 1, 4: 2, 9: 3, 16: 4, 25: 5}
    while True:
        if arg is None:
            print("\nRejillas disponibles:  n = 1 (1×1),  4 (2×2),  9 (3×3),  16 (4×4),  25 (5×5, sólo resumen)")
            s = input("Elija n: ").strip()
        else:
            s = str(arg); arg = None
        try:
            n = int(s)
        except ValueError:
            print("Escriba un número."); continue
        if n in validos:
            return n, validos[n]
        r = int(round(math.sqrt(n)))
        if r * r == n and n <= 16:
            return n, r
        print("n debe ser 1, 4, 9, 16 o 25.")


def menu(P):
    fmt = P.fmt
    opciones = """
--------------------------------------------------------------
  1  La red (vértices, aristas, vecindades)
  2  El autómata (reglas locales y tabla de F)
  3  Puntos fijos
  4  Puntos periódicos y sus períodos
  5  Atractores Att(G)
  6  Cuencas de atracción (lista de configuraciones por niveles)
  7  Paisaje de atractores (resumen completo)
  8  Trayectoria de una configuración que usted escriba
  9  Guardar reporte completo en un archivo .txt
  0  Cambiar de rejilla / salir
--------------------------------------------------------------"""
    while True:
        print(opciones)
        op = input("Opción: ").strip()
        if op == "1":
            print(P.s_red())
        elif op == "2":
            print(P.s_automata())
        elif op == "3":
            print(P.s_fijos())
        elif op == "4":
            print(P.s_periodicos())
        elif op == "5":
            print(P.s_atractores())
        elif op == "6":
            lim = input("Máximo de configuraciones a mostrar por cuenca (Enter = todas): ").strip()
            print(P.s_cuencas(int(lim) if lim else None))
        elif op == "7":
            print(P.s_paisaje())
        elif op == "8":
            ejemplo = "(1,0,1,0)" if P.R.m == 2 else ("0" if P.R.m == 1 else "/".join(["0" * P.R.m] * (P.R.m - 1) + ["1" * P.R.m]))
            s = input(f"Configuración (por ejemplo {ejemplo}): ")
            try:
                x = fmt.leer(s)
                print(P.s_trayectoria(x))
            except ValueError as e:
                print("Formato no válido:", e)
        elif op == "9":
            nombre = f"paisaje_{P.R.m}x{P.R.m}.txt"
            with open(nombre, "w", encoding="utf-8") as f:
                f.write(P.reporte(completo=True))
            print(f"Reporte guardado en {nombre}")
        elif op == "0":
            return
        else:
            print("Opción no válida.")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    todo = "--todo" in sys.argv
    n, m = elegir_n(args[0] if args else None)
    while True:
        if n == 25:
            try:
                print(resumen_numpy(5))
            except ImportError:
                print("Para n = 25 se necesita numpy (pip install numpy).")
            except MemoryError:
                print("Memoria insuficiente para n = 25.")
        else:
            print(f"\nCalculando el paisaje de la rejilla {m}×{m} ({2 ** n} configuraciones)...")
            P = Paisaje(Rejilla(m))
            print("Listo.")
            if todo:
                print(P.reporte(completo=True))
                nombre = f"paisaje_{m}x{m}.txt"
                with open(nombre, "w", encoding="utf-8") as f:
                    f.write(P.reporte(completo=True))
                print(f"\nReporte guardado en {nombre}")
                return
            menu(P)
        s = input("\n¿Otra rejilla? (Enter = sí, 'n' = salir): ").strip().lower()
        if s == "n":
            return
        n, m = elegir_n()


if __name__ == "__main__":
    main()
