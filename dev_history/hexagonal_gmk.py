# -*- coding: utf-8 -*-
"""Build the Gamma-M-K-Gamma plot from Table IV ranges and Appendix B fold.

Rules (Jimenez-Suarez et al., IEEE TMTT 73(9), 2025):
  Table IV   Gamma-M : SC Delta phi_y = [0, 2*pi]
             Gamma-K1: SC Delta phi_x = [0, 4*pi/3]
  Appendix B Gamma-K1 branches: fundamental (0..pi plus pi..4pi/3 folded
             by 2*pi - phi_x) -> PC Gamma-K; backward mode (0..2pi/3) -> PC K-M.
Branch assignment here is heuristic (frequency continuity), not a strict
MMTMM eigensolution classification.
"""
import csv
import os
import re

ROOT = r"D:\document\Workbuddy\2026-11-07-22-48-25\tensor_patch"
FULL = os.path.join(ROOT, "eig_hexagonal_ibz_full")
SYM = os.path.join(ROOT, "eig_hexagonal_sym")
OUT_MODES = os.path.join(ROOT, "hexagonal_sym_modes.csv")
OUT_PATH = os.path.join(ROOT, "hexagonal_GMK_path.csv")
OUT_PNG = os.path.join(ROOT, "hexagonal_GMK_path.png")


def parse(path, n=5):
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


def series(folder, prefix, phases):
    return {p: parse(os.path.join(folder, "%s_%d.eig" % (prefix, p)))
            for p in phases}


def main():
    gm_p = list(range(0, 361, 30))
    gk_p = list(range(0, 241, 30))
    sym_p = list(range(0, 241, 30))
    gm = series(FULL, "GM", gm_p)
    gk = series(FULL, "GK1", gk_p)
    even = series(SYM, "even", sym_p)
    odd = series(SYM, "odd", sym_p)

    with open(OUT_MODES, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["parity", "phi_x_deg"] +
                   ["f%d_GHz" % i for i in range(1, 6)])
        for parity, data in (("even (M-M PMC)", even), ("odd (E-E PEC)", odd)):
            for p in sym_p:
                w.writerow([parity, p] + data[p])

    rows = []
    # Gamma -> M, s in [0,1]. SC phi_y 0..pi forward, pi..2pi folded back.
    for p in gm_p:
        s = (p if p <= 180 else 360 - p) / 180.0
        tag = "GM_fwd" if p <= 180 else "GM_fold"
        for k in (0, 1):
            if gm[p][k] is not None:
                rows.append(["GM", tag, p, round(s, 4), k + 1, gm[p][k]])
    # K -> Gamma, s in [2,3]. Fundamental branch of Gamma-K1.
    for p in gk_p:
        if p <= 180:
            s = 2.0 + (180 - p) / 180.0
            tag = "KGamma_fwd"
        else:
            folded = 360 - p
            s = 2.0 + (180 - folded) / 180.0
            tag = "KGamma_fold"
        for k in (0, 1):
            if gk[p][k] is not None:
                rows.append(["KGamma", tag, p, round(s, 4), k + 1, gk[p][k]])
    # M -> K, s in [1,2]. Backward mode over 0..2pi/3.
    for p in gk_p:
        if p <= 120:
            s = 1.0 + (120 - p) / 120.0
            for k in (0, 1):
                if gk[p][k] is not None:
                    rows.append(["MK", "GK1_back", p, round(s, 4),
                                 k + 1, gk[p][k]])
    # Parity markers on the K->Gamma segment.
    for parity, data in (("even", even), ("odd", odd)):
        for p in sym_p:
            if p <= 180 and data[p][0] is not None:
                s = 2.0 + (180 - p) / 180.0
                rows.append(["parity", parity, p, round(s, 4), 1, data[p][0]])

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["pc_segment", "branch", "sc_phase_deg",
                    "path_s", "mode", "f_GHz"])
        for r in rows:
            w.writerow(r)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=175)
        styles = (("GM_fwd", "#d62728", "o-", "Gamma-M fwd"),
                  ("GM_fold", "#d62728", "s--", "Gamma-M folded"),
                  ("GK1_back", "#3B6D11", "^-", "M-K backward"),
                  ("KGamma_fwd", "#185FA5", "o-", "K-Gamma fwd"),
                  ("KGamma_fold", "#185FA5", "s--", "K-Gamma folded"))
        for tag, color, style, label in styles:
            pts = [r for r in rows if r[1] == tag and r[4] == 1]
            if pts:
                pts.sort(key=lambda r: r[3])
                ax.plot([r[3] for r in pts], [r[5] for r in pts], style,
                        ms=3.5, lw=1.4, color=color, label=label)
        for parity, marker, color in (("even", "D", "#9467bd"),
                                      ("odd", "v", "#ff7f0e")):
            pts = [r for r in rows if r[1] == parity]
            ax.scatter([r[3] for r in pts], [r[5] for r in pts],
                       marker=marker, s=26, color=color, zorder=5,
                       label="%s symmetry plane" % parity)
        for x, name in ((0, "Gamma"), (1, "M"), (2, "K"), (3, "Gamma")):
            ax.axvline(x, color="#888780", ls=":", lw=1)
        ax.set_xticks([0, 1, 2, 3])
        ax.set_xticklabels(["Gamma", "M", "K", "Gamma"])
        ax.set_xlabel("IBZ path")
        ax.set_ylabel("f (GHz)")
        ax.set_title("Gamma-M-K-Gamma, Table IV ranges + Appendix B fold")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=7.5, ncol=2)
        fig.tight_layout()
        fig.savefig(OUT_PNG)
        plt.close(fig)
        print("plot written", OUT_PNG, flush=True)
    except Exception as exc:
        print("plot failed", repr(exc), flush=True)

    print("path rows", len(rows), flush=True)
    print("Gamma: full", gm[0][:2], "even", even[0][:2],
          "odd", odd[0][:2], flush=True)


if __name__ == "__main__":
    main()
