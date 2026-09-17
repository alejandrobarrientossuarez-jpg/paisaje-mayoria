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
  * las cuencas de atracción  B(A)  con sus niveles (profundidad τ de cada
    configuración = número de iteraciones hasta entrar al atractor),
  * el paisaje L(G): tamaños, profundidad máxima, Jardines del Edén, cuencas
    de sincronización B0, B1, B_sync y fracción sincronizante,
  * la trayectoria de cualquier configuración que el usuario escriba.

Valores de n previstos: 1, 4, 9, 16 (rejillas 1×1, 2×2, 3×3, 4×4) con el
motor exacto en Python puro, y 25 (5×5, 33 554 432 configuraciones) con el
motor vectorizado (requiere numpy y ~2 GB de memoria libre).

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
        if m == 2:
            self.etiquetas = ["a", "b", "c", "d"]
            self.pos = {0: (0, 0), 1: (0, 1), 2: (1, 1), 3: (1, 0)}
        else:
            self.etiquetas = [str(k + 1) for k in range(self.n)]
            self.pos = {k: (k // m, k % m) for k in range(self.n)}
        self.idx_de_pos = {p: k for k, p in self.pos.items()}
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
        out = [f"Rejilla {m}×{m}: n = {self.n} vértices, {len(self.aristas)} aristas."]
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
        m = self.R.m
        return "/".join("".join(str(x[self.R.idx_de_pos[(i, j)]]) for j in range(m)) for i in range(m))

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
                    if ch not in "01":
                        raise ValueError("sólo se admiten 0 y 1")
                    x[self.R.idx_de_pos[(i, j)]] = int(ch)
            return tuple(x)
        s = s.strip("()[]").replace(",", "")
        if len(s) != n or any(ch not in "01" for ch in s):
            raise ValueError("se esperaban %d dígitos 0/1" % n)
        return tuple(int(ch) for ch in s)


# ---------------------------------------------------------------------------
# 4. INTERFAZ COMÚN DE UN PAISAJE (la usan el menú de consola y la app)
# ---------------------------------------------------------------------------

class PaisajeBase:
    """Métodos de presentación comunes; las subclases implementan los accesos:
    n_X, atractores, fijos, ciclos, periodicos, profundidad_max, n_eden, id_cero, id_uno,
    todas(), sig_de(x), profundidad_de(x), atractor_de(x), tam_cuenca(i), niveles(i),
    miembros(i, maximo), preimagenes(x), eden_lista(maximo), histograma_profundidad()."""

    def periodo(self, x):
        return len(self.atractores[self.atractor_de(x)]) if self.profundidad_de(x) == 0 else None

    def trayectoria(self, x):
        tr, vistos = [x], {x}
        y = self.sig_de(x)
        while y not in vistos:
            tr.append(y)
            vistos.add(y)
            y = self.sig_de(y)
        return tr, y

    def sincroniza(self, x):
        return self.atractor_de(x) in (self.id_cero, self.id_uno)

    # ---- secciones de texto ----
    def s_red(self):
        return "1. LA RED\n" + "=" * 60 + "\n" + self.R.describir()

    def s_automata(self, tabla_max=64):
        R, fmt = self.R, self.fmt
        out = ["2. EL AUTÓMATA DE MAYORÍA", "=" * 60]
        out.append(f"Espacio de configuraciones X = {{0,1}}^{R.n}, |X| = 2^{R.n} = {self.n_X:,}.")
        out.append("Regla local (empate → conserva), escrita por vértice:")
        for k in range(R.n):
            vec = ", ".join(R.et(u) for u in sorted(R.N[k]))
            d = R.deg[k]
            regla = {2: "copia a sus dos vecinos si coinciden; si difieren conserva su estado",
                     3: "toma el valor mayoritario de sus tres vecinos (sin empates)",
                     4: "1 si ≥3 vecinos en 1; 0 si ≤1; conserva si exactamente 2",
                     1: "copia a su único vecino", 0: "sin vecinos: conserva"}[d]
            out.append(f"   {R.et(k)}' = f_{R.et(k)}({vec}) : {regla}")
        if self.n_X <= tabla_max:
            out.append("")
            out.append("Tabla completa de F_G (x → F_G(x)):")
            for x in self.todas():
                y = self.sig_de(x)
                out.append(f"   {fmt.corto(x)} → {fmt.corto(y)}" + ("  ← punto fijo" if y == x else ""))
        else:
            out.append(f"(La tabla completa tiene {self.n_X:,} renglones; use la opción 'trayectoria' para consultar configuraciones concretas.)")
        return "\n".join(out)

    def s_fijos(self):
        fmt = self.fmt
        out = ["3. PUNTOS FIJOS  Fix(G) = { x : F_G(x) = x }", "=" * 60, f"|Fix(G)| = {len(self.fijos):,}"]
        for i, x in enumerate(self.fijos, 1):
            out.append(f"   {i:>5}. {fmt.largo(x)}   cuenca de tamaño {self.tam_cuenca(self.atractor_de(x)):,}")
        out.append("Criterio de verificación: ningún vértice tiene más vecinos contrarios que deg(v)/2.")
        return "\n".join(out)

    def s_periodicos(self):
        fmt = self.fmt
        out = ["4. PUNTOS PERIÓDICOS  Per(G) = { x : F_G^p(x) = x para algún p ≥ 1 }", "=" * 60]
        por_p = Counter(p for _, p in self.periodicos)
        out.append(f"|Per(G)| = {len(self.periodicos):,}   " + ", ".join(f"período {p}: {c:,}" for p, c in sorted(por_p.items())))
        out.append(f"Puntos transitorios: |X \\ Per(G)| = {self.n_X - len(self.periodicos):,}")
        out.append("")
        out.append("   configuración                      período   órbita periódica O(x)")
        for x, p in self.periodicos:
            A = self.atractores[self.atractor_de(x)]
            orbita = " ⇄ ".join(fmt.corto(c) for c in A) if p > 1 else "{" + fmt.corto(x) + "}"
            out.append(f"   {fmt.largo(x):<34} {p:>5}     {orbita}")
        return "\n".join(out)

    def s_atractores(self):
        fmt = self.fmt
        out = ["5. ATRACTORES  Att(G) (órbitas periódicas)", "=" * 60]
        out.append(f"|Att(G)| = {len(self.atractores):,}   ({len(self.fijos):,} puntos fijos, {len(self.ciclos):,} ciclos de longitud 2)")
        for i, A in enumerate(self.atractores, 1):
            out.append(f"   A{i:<5} = {{ {', '.join(fmt.corto(c) for c in A)} }}   período {len(A)}   |B(A{i})| = {self.tam_cuenca(i - 1):,}")
        if len(self.atractores) <= 500:
            out.append("Att(G) = { " + ", ".join("{" + ", ".join(fmt.corto(c) for c in A) + "}" for A in self.atractores) + " }")
        return "\n".join(out)

    def s_cuencas(self, max_por_cuenca=None):
        fmt = self.fmt
        out = ["6. CUENCAS DE ATRACCIÓN  B(A) = { x : F_G^t(x) ∈ A para algún t }", "=" * 60]
        tam = [self.tam_cuenca(i) for i in range(len(self.atractores))]
        out.append("Tamaños: " + ", ".join(f"|B(A{i + 1})|={t:,}" for i, t in enumerate(tam)))
        out.append(f"Verificación de partición: suma = {sum(tam):,} = |X| ✓" if sum(tam) == self.n_X else "ERROR en la partición")
        for i, A in enumerate(self.atractores):
            niv = self.niveles(i)
            out.append("")
            out.append(f"B(A{i + 1}), atractor {{ {', '.join(fmt.corto(c) for c in A)} }}: {tam[i]:,} configuraciones; "
                       "niveles " + ", ".join(f"L{k}={v:,}" for k, v in enumerate(niv)))
            for x in self.miembros(i, max_por_cuenca):
                h = self.profundidad_de(x)
                flecha = "(en el atractor)" if h == 0 else f"→ {fmt.corto(self.sig_de(x))}"
                out.append(f"      τ={h:<2} {fmt.corto(x):<28} {flecha}")
            if max_por_cuenca is not None and tam[i] > max_por_cuenca:
                out.append(f"      ... ({tam[i] - max_por_cuenca:,} configuraciones más)")
        return "\n".join(out)

    def s_paisaje(self):
        fmt = self.fmt
        B0, B1 = self.tam_cuenca(self.id_cero), self.tam_cuenca(self.id_uno)
        out = ["7. PAISAJE DE ATRACTORES  L(G) = { (A, B(A)) : A ∈ Att(G) }", "=" * 60]
        out.append(f"|X| = {self.n_X:,}")
        out.append(f"Atractores: {len(self.atractores):,}  (fijos: {len(self.fijos):,}, 2-ciclos: {len(self.ciclos):,})")
        out.append(f"Puntos periódicos: {len(self.periodicos):,}   transitorios: {self.n_X - len(self.periodicos):,}")
        out.append(f"Profundidad máxima del paisaje: {self.profundidad_max}")
        out.append("Configuraciones por profundidad τ: " + ", ".join(f"τ={k}: {v:,}" for k, v in enumerate(self.histograma_profundidad())))
        out.append(f"Jardines del Edén (sin preimagen): {self.n_eden:,}  ({100 * self.n_eden / self.n_X:.2f} %)")
        out.append(f"|B0| = {B0:,}, |B1| = {B1:,}, |B_sync| = {B0 + B1:,}  ({100 * (B0 + B1) / self.n_X:.2f} % de X)")
        out.append("Niveles de B0: " + ", ".join(f"L{k}={v:,}" for k, v in enumerate(self.niveles(self.id_cero))))
        out.append("Globalmente sincronizante: " + ("SÍ" if B0 + B1 == self.n_X else "NO"))
        out.append("")
        out.append("   atractor                                       período   |B(A)|   profundidad máx.")
        for i, A in enumerate(self.atractores):
            niv = self.niveles(i)
            out.append(f"   A{i + 1:<5} {' ⇄ '.join(fmt.corto(c) for c in A):<44} {len(A):>5}   {self.tam_cuenca(i):>9,}   {len(niv) - 1:>5}")
        ed = self.eden_lista(64)
        if self.n_eden <= 64 and ed:
            out.append("")
            out.append("Jardines del Edén: " + ", ".join(fmt.corto(x) for x in ed))
        return "\n".join(out)

    def s_trayectoria(self, x):
        fmt = self.fmt
        tr, _ = self.trayectoria(x)
        aid = self.atractor_de(x)
        A = self.atractores[aid]
        h = self.profundidad_de(x)
        out = [f"Trayectoria de {fmt.largo(x)}:"]
        for t, y in enumerate(tr):
            out.append(f"   t={t:<3} {fmt.corto(y)}" + ("   (entra al atractor)" if t == h and h > 0 else ""))
        out.append(f"Profundidad τ(x) = {h};  atractor A{aid + 1} = {{ {', '.join(fmt.corto(c) for c in A)} }} (período {len(A)});  |B(A{aid + 1})| = {self.tam_cuenca(aid):,}")
        p = self.periodo(x)
        out.append("Es punto periódico de período %d." % p if p else "Es punto transitorio (no periódico).")
        out.append("Es punto fijo." if self.sig_de(x) == x else "No es punto fijo.")
        npre = len(self.preimagenes(x))
        out.append("Es Jardín del Edén (sin preimagen)." if npre == 0 else f"Tiene {npre} preimagen(es).")
        out.append(f"Sincroniza: T_sync = {h}." if self.sincroniza(x) else "No sincroniza (no cae en 0 ni en 1).")
        return "\n".join(out)

    def reporte(self, completo=True):
        return "\n\n".join([self.s_red(), self.s_automata(tabla_max=(self.n_X if completo else 64)), self.s_fijos(),
                            self.s_periodicos(), self.s_atractores(), self.s_cuencas(None if completo else 12), self.s_paisaje()])


# ---------------------------------------------------------------------------
# 5. MOTOR EXACTO EN PYTHON PURO (n ≤ 16)
# ---------------------------------------------------------------------------

class Paisaje(PaisajeBase):
    """Enumeración exhaustiva con diccionarios; guarda todo en memoria."""

    def __init__(self, R):
        self.R = R
        self.fmt = Formato(R)
        self.X = list(itertools.product((0, 1), repeat=R.n))
        self.n_X = len(self.X)
        self.sig = {x: F(x, R.N) for x in self.X}
        self._clasificar()

    def _clasificar(self):
        sig = self.sig
        self._aid, self._prof, self.atractores = {}, {}, []
        for x in self.X:
            if x in self._aid:
                continue
            camino, visto, y = [], {}, x
            while y not in self._aid and y not in visto:
                visto[y] = len(camino)
                camino.append(y)
                y = sig[y]
            if y in self._aid:
                aid, h = self._aid[y], self._prof[y]
                for z in reversed(camino):
                    h += 1
                    self._aid[z], self._prof[z] = aid, h
            else:
                k = visto[y]
                ciclo = camino[k:]
                aid = len(self.atractores)
                self.atractores.append(tuple(ciclo))
                for z in ciclo:
                    self._aid[z], self._prof[z] = aid, 0
                h = 0
                for z in reversed(camino[:k]):
                    h += 1
                    self._aid[z], self._prof[z] = aid, h
        tam = Counter(self._aid.values())
        n = self.R.n
        cero, uno = tuple([0] * n), tuple([1] * n)

        def clave(aid):
            A = self.atractores[aid]
            if A == (cero,):
                return (0, 0, 0)
            if A == (uno,):
                return (0, 1, 0)
            return (len(A), -tam[aid], A)
        orden = sorted(range(len(self.atractores)), key=clave)
        nuevo = {old: new for new, old in enumerate(orden)}
        self.atractores = [self.atractores[o] for o in orden]
        self._aid = {x: nuevo[a] for x, a in self._aid.items()}
        self._cuenca = defaultdict(list)
        for x in self.X:
            self._cuenca[self._aid[x]].append(x)
        for aid in self._cuenca:
            self._cuenca[aid].sort(key=lambda z: (self._prof[z], self.fmt.corto(self.sig[z]), z))
        self._pre = defaultdict(list)
        for x in self.X:
            self._pre[sig[x]].append(x)
        self.fijos = [A[0] for A in self.atractores if len(A) == 1]
        self.ciclos = [A for A in self.atractores if len(A) >= 2]
        self.periodicos = [(x, len(self.atractores[self._aid[x]])) for x in self.X if self._prof[x] == 0]
        self.profundidad_max = max(self._prof.values())
        self._eden = [x for x in self.X if x not in self._pre]
        self.n_eden = len(self._eden)
        self.id_cero = self._aid[cero]
        self.id_uno = self._aid[uno]

    def todas(self):
        return self.X

    def sig_de(self, x):
        return self.sig[x]

    def profundidad_de(self, x):
        return self._prof[x]

    def atractor_de(self, x):
        return self._aid[x]

    def tam_cuenca(self, i):
        return len(self._cuenca[i])

    def niveles(self, i):
        c = Counter(self._prof[x] for x in self._cuenca[i])
        return [c[k] for k in range(max(c) + 1)]

    def miembros(self, i, maximo=None):
        return self._cuenca[i] if maximo is None else self._cuenca[i][:maximo]

    def preimagenes(self, x):
        return self._pre.get(x, [])

    def eden_lista(self, maximo=None):
        return self._eden if maximo is None else self._eden[:maximo]

    def histograma_profundidad(self):
        c = Counter(self._prof.values())
        return [c[k] for k in range(max(c) + 1)]


# ---------------------------------------------------------------------------
# 6. MOTOR VECTORIZADO CON NUMPY (n = 25)
# ---------------------------------------------------------------------------

class PaisajeNumpy(PaisajeBase):
    """Enumeración exhaustiva con numpy; misma interfaz que Paisaje. Requiere ~2 GB para 5×5."""

    def __init__(self, R, avisar=print):
        import numpy as np
        self.np = np
        self.R = R
        self.fmt = Formato(R)
        n = R.n
        size = 1 << n
        self.n_X = size
        avisar(f"Calculando F_G para {size:,} configuraciones...")
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
        self.sig = sig
        avisar("Clasificando puntos periódicos y profundidades...")
        per = (sig[sig] == idx)
        cur = idx.copy()
        h = np.zeros(size, dtype=np.uint8)
        act = np.flatnonzero(~per[cur])
        while act.size:
            cur[act] = sig[cur[act]]
            h[act] += 1
            act = act[~per[cur[act]]]
        rep = np.minimum(cur, sig[cur])
        del cur, per, idx
        self.h = h
        avisar("Agrupando cuencas...")
        self.orden_rep = np.argsort(rep, kind="stable")
        rep_ord = rep[self.orden_rep]
        cambios = np.flatnonzero(np.diff(rep_ord.astype(np.int64))) + 1
        self.inicios = np.concatenate(([0], cambios, [size])).astype(np.int64)
        reps = rep_ord[self.inicios[:-1]]
        tam = np.diff(self.inicios)
        del rep_ord
        info = []
        for r, t in zip(reps.tolist(), tam.tolist()):
            x = self.int_a_tupla(r)
            y = F(x, R.N)
            info.append(((x,) if y == x else (x, y), r, t))
        cero, uno = 0, size - 1

        def clave(item):
            A, r, t = item
            if r == cero:
                return (0, 0, 0)
            if r == uno:
                return (0, 1, 0)
            return (len(A), -t, A)
        info.sort(key=clave)
        self.atractores = [A for A, r, t in info]
        self._rep_de_aid = [r for A, r, t in info]
        self._tam = [t for A, r, t in info]
        self._grupo = {r: pos for pos, r in enumerate(reps.tolist())}
        self._aid_de_rep = {r: i for i, r in enumerate(self._rep_de_aid)}
        self.rep = rep
        self.fijos = [A[0] for A in self.atractores if len(A) == 1]
        self.ciclos = [A for A in self.atractores if len(A) >= 2]
        avisar("Puntos periódicos...")
        perid = np.flatnonzero(h == 0)
        self.periodicos = [(self.int_a_tupla(int(v)), len(self.atractores[self.atractor_de_int(int(v))])) for v in perid.tolist()]
        self.profundidad_max = int(h.max())
        avisar("Jardines del Edén (ordenando imágenes)...")
        self.orden_sig = np.argsort(sig, kind="stable")
        self.sig_ord = sig[self.orden_sig]
        self.n_eden = int(size - np.unique(self.sig_ord).size)
        self.id_cero = self._aid_de_rep[cero]
        self.id_uno = self._aid_de_rep[uno]
        self._hist = np.bincount(h).tolist()
        avisar("Listo.")

    def int_a_tupla(self, v):
        return tuple((v >> k) & 1 for k in range(self.R.n))

    def tupla_a_int(self, x):
        return sum(b << k for k, b in enumerate(x))

    def todas(self):
        return (self.int_a_tupla(v) for v in range(self.n_X))

    def sig_de(self, x):
        return self.int_a_tupla(int(self.sig[self.tupla_a_int(x)]))

    def profundidad_de(self, x):
        return int(self.h[self.tupla_a_int(x)])

    def atractor_de_int(self, v):
        return self._aid_de_rep[int(self.rep[v])]

    def atractor_de(self, x):
        return self.atractor_de_int(self.tupla_a_int(x))

    def tam_cuenca(self, i):
        return self._tam[i]

    def _slice(self, i):
        pos = self._grupo[self._rep_de_aid[i]]
        return self.orden_rep[self.inicios[pos]:self.inicios[pos + 1]]

    def niveles(self, i):
        return self.np.bincount(self.h[self._slice(i)]).tolist()

    def miembros(self, i, maximo=None):
        ids = self._slice(i)
        ids = ids[self.np.argsort(self.h[ids], kind="stable")]
        if maximo is not None:
            ids = ids[:maximo]
        return [self.int_a_tupla(int(v)) for v in ids.tolist()]

    def preimagenes(self, x):
        v = self.tupla_a_int(x)
        a = self.np.searchsorted(self.sig_ord, v, "left")
        b = self.np.searchsorted(self.sig_ord, v, "right")
        return [self.int_a_tupla(int(w)) for w in self.orden_sig[a:b].tolist()]

    def eden_lista(self, maximo=None):
        return []            # decenas de millones: no se enumeran

    def histograma_profundidad(self):
        return self._hist


# ---------------------------------------------------------------------------
# 7. INTERFAZ DE CONSOLA
# ---------------------------------------------------------------------------

def construir(n, avisar=print):
    m = int(round(math.sqrt(n)))
    if m * m != n:
        raise ValueError("n debe ser un cuadrado perfecto")
    return Paisaje(Rejilla(m)) if n <= 16 else PaisajeNumpy(Rejilla(m), avisar)


def elegir_n(arg=None):
    validos = {1, 4, 9, 16, 25}
    while True:
        if arg is None:
            print("\nRejillas disponibles:  n = 1 (1×1),  4 (2×2),  9 (3×3),  16 (4×4),  25 (5×5, requiere numpy y ~2 GB)")
            s = input("Elija n: ").strip()
        else:
            s = str(arg); arg = None
        try:
            n = int(s)
        except ValueError:
            print("Escriba un número."); continue
        if n in validos:
            return n
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
  9  Guardar reporte en un archivo .txt
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
            print(P.s_cuencas(int(lim) if lim else (None if P.n_X <= 65536 else 20)))
        elif op == "7":
            print(P.s_paisaje())
        elif op == "8":
            m = P.R.m
            ejemplo = "(1,0,1,0)" if m == 2 else ("0" if m == 1 else "/".join(["0" * m] * (m - 1) + ["1" * m]))
            s = input(f"Configuración (por ejemplo {ejemplo}): ")
            try:
                print(P.s_trayectoria(fmt.leer(s)))
            except ValueError as e:
                print("Formato no válido:", e)
        elif op == "9":
            nombre = f"paisaje_{P.R.m}x{P.R.m}.txt"
            with open(nombre, "w", encoding="utf-8") as f:
                f.write(P.reporte(completo=(P.n_X <= 65536)))
            print(f"Reporte guardado en {nombre}")
        elif op == "0":
            return
        else:
            print("Opción no válida.")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    todo = "--todo" in sys.argv
    n = elegir_n(args[0] if args else None)
    while True:
        m = int(round(math.sqrt(n)))
        print(f"\nCalculando el paisaje de la rejilla {m}×{m} ({2 ** n:,} configuraciones)...")
        try:
            P = construir(n)
        except ImportError:
            print("Para n = 25 se necesita numpy (pip install numpy)."); return
        except MemoryError:
            print("Memoria insuficiente para n = 25."); return
        print("Listo.")
        if todo:
            texto = P.reporte(completo=(P.n_X <= 65536))
            print(texto)
            nombre = f"paisaje_{m}x{m}.txt"
            with open(nombre, "w", encoding="utf-8") as f:
                f.write(texto)
            print(f"\nReporte guardado en {nombre}")
            return
        menu(P)
        s = input("\n¿Otra rejilla? (Enter = sí, 'n' = salir): ").strip().lower()
        if s == "n":
            return
        n = elegir_n()


if __name__ == "__main__":
    main()
