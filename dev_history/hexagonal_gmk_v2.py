# -*- coding: utf-8 -*-
"""Parity-resolved Gamma-M-K-Gamma reconstruction.

Spectra available:
  x-direction half supercell (phi_x fixed by M^x/E^x planes, sweeps phi_y 0..2pi)
    -> even / odd branches of the Gamma-M segment.
  y-direction half supercell (phi_y fixed by M^y/E^y planes, sweeps phi_x 0..4pi/3)
    -> even / odd branches of the Gamma-K1 segment (Appendix B source).
  full supercell GM / GK1 scans as reference.

Branch-to-path assignment is still heuristic. Parity labels are strict
(PEC/PMC symmetry planes), which is the improvement over the previous plot.
"""
import csv
import os
import re

ROOT = r"D:\document\Workbuddy\2026-11-07-22-48-25\tensor_patch"
DIR_X = os.path.join(ROOT, "eig_hexagonal_symx")
DIR_Y = os.path.join(ROOT, "eig_hexagonal_sym")
DIR_FULL = os.path.join(ROOT, "eig_hexagonal_ibz_full")
OUT_MODES = os.path.join(ROOT, "hexagonal_parity_modes.csv")
OUT_RES = os.path.join(ROOT, "hexagonal_parity_residual.csv")
OUT_PNG = os.path.join(ROOT, "hexagonal_GMK_parity.png")

X_PHASES = tuple(range(0, 361, 30))
Y_PHASES = tuple(range(0, 241, 30))


def parse(path, n=6):
    if not os.path.exists(path):
        return [None] * n
    out = []
    for line in open(path, encoding="utf-8-sig", errors="ignore"):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        t = s.split()
        if len(t) >= 2:
            try:
                out.append(round(float(t[1]), 6))
            except ValueError:
                m = re.match(r"^\s*\d+\s+([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", s)
                if m:
                    out.append(round(float(m.group(1)), 6))
    return (out + [None] * n)[:n]


def load(folder, prefix, phases):
    return {p: parse(os.path.join(folder, "%s_%d.eig" % (prefix, p)))
            for p in phases}


def numeric(vals):
    return [v for v in vals if v is not None]


def best_pair(a, b):
    """Smallest frequency gap between two branch sets."""
    best = None
    for x in numeric(a):
        for y in numeric(b):
            gap = abs(x - y)
            if best is None or gap < best[0]:
                best = (gap, x, y)
    return best


def main():
    xe = load(DIR_X, "even", X_PHASES)
    xo = load(DIR_X, "odd", X_PHASES)
    ye = load(DIR_Y, "even", Y_PHASES)
    yo = load(DIR_Y, "odd", Y_PHASES)
    gm = load(DIR_FULL, "GM", X_PHASES)
    gk = load(DIR_FULL, "GK1", Y_PHASES)

    with open(OUT_MODES, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["spectrum", "phase_deg"] +
                   ["f%d_GHz" % i for i in range(1, 7)])
        for name, data in (("x_even", xe), ("x_odd", xo),
                           ("y_even", ye), ("y_odd", yo),
                           ("full_GM", gm), ("full_GK1", gk)):
            for p in sorted(data):
                w.writerow([name, p] + data[p])

    # Residual at M and K between parity-resolved branch sets.
    residual = []
    for label, a, b in (
            ("M even: Gamma-M(phi_y=180) vs M-K(phi_x=120)",
             xe.get(180, []), ye.get(120, [])),
            ("M odd: Gamma-M(phi_y=180) vs M-K(phi_x=120)",
             xo.get(180, []), yo.get(120, [])),
            ("M even alt: Gamma-M(phi_y=360) vs M-K(phi_x=120)",
             xe.get(360, []), ye.get(120, [])),
            ("M odd alt: Gamma-M(phi_y=360) vs M-K(phi_x=120)",
             xo.get(360, []), yo.get(120, [])),
            ("K even: M-K(phi_x=0) vs K-Gamma(phi_x=180)",
             ye.get(0, []), ye.get(180, [])),
            ("K odd: M-K(phi_x=0) vs K-Gamma(phi_x=180)",
             yo.get(0, []), yo.get(180, [])),
            ("K even alt: M-K(phi_x=0) vs K-Gamma(phi_x=120)",
             ye.get(0, []), ye.get(120, [])),
            ("K odd alt: M-K(phi_x=0) vs K-Gamma(phi_x=120)",
             yo.get(0, []), yo.get(120, []))):
        pair = best_pair(a, b)
        if pair:
            residual.append([label, round(pair[0], 6), pair[1], pair[2]])
            print(label, "residual", round(pair[0], 6), "GHz", flush=True)
    with open(OUT_RES, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["junction", "min_gap_GHz", "f_a_GHz", "f_b_GHz"])
        for r in residual:
            w.writerow(r)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8.8, 5.0), dpi=175)
        # Gamma-M: folded phi_y 0..pi, one curve per parity.
        for name, data, color, marker in (("even", xe, "#185FA5", "o"),
                                          ("odd", xo, "#d62728", "s")):
            xs, ys = [], []
            for p in X_PHASES:
                if p <= 180 and data[p][0] is not None:
                    xs.append(p / 180.0)
                    ys.append(data[p][0])
            ax.plot(xs, ys, marker + "-", ms=3.5, lw=1.4, color=color,
                    label="Gamma-M %s (M-M)" % name if name == "even"
                    else "Gamma-M %s (E-E)" % name)
        # M-K and K-Gamma: parity-resolved Gamma-K1 branches.
        for name, data, color, ls in (("even", ye, "#185FA5", "-"),
                                      ("odd", yo, "#d62728", "-")):
            xs, ys = [], []
            for p in Y_PHASES:
                if p <= 120 and data[p][0] is not None:
                    xs.append(1.0 + (120 - p) / 120.0)
                    ys.append(data[p][0])
            ax.plot(xs, ys, "^" + ls, ms=3.5, lw=1.2, color=color,
                    alpha=0.75, label="M-K %s" % name)
            xs2, ys2 = [], []
            for p in Y_PHASES:
                if p <= 180 and data[p][0] is not None:
                    xs2.append(2.0 + (180 - p) / 180.0)
                    ys2.append(data[p][0])
            ax.plot(xs2, ys2, "v" + ls, ms=3.5, lw=1.2, color=color,
                    alpha=0.75, label="K-Gamma %s" % name)
        for x, name in ((0, "Gamma"), (1, "M"), (2, "K"), (3, "Gamma")):
            ax.axvline(x, color="#888780", ls=":", lw=1)
        ax.set_xticks([0, 1, 2, 3])
        ax.set_xticklabels(["Gamma", "M", "K", "Gamma"])
        ax.set_xlabel("IBZ path")
        ax.set_ylabel("f (GHz)")
        ax.set_title("Parity-resolved Gamma-M-K-Gamma (branch assignment heuristic)")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=7, ncol=2)
        fig.tight_layout()
        fig.savefig(OUT_PNG)
        plt.close(fig)
        print("plot written", OUT_PNG, flush=True)
    except Exception as exc:
        print("plot failed", repr(exc), flush=True)

    print("Gamma x_even/x_odd", xe.get(0, [])[:2], xo.get(0, [])[:2],
          "full", gm.get(0, [])[:2], flush=True)


if __name__ == "__main__":
    main()
