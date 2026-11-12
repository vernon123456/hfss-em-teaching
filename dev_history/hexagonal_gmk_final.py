# -*- coding: utf-8 -*-
"""Gamma-M-K-Gamma with the corrected M->K direction.

Appendix B fold (IEEE TMTT 73(9), 2025):
  Gamma-M : full supercell phi_y 0..pi (SC 0..2pi folded), endpoint phi_y=2pi = M0
  M-K     : y_ee (E^y_0 E^y_py/2) phi_x 0..2pi/3, start phi_x=0 = M0, end = K
  K-Gamma : y_mm (M^y_0 M^y_py/2) phi_x 4pi/3..0, start = K, end = Gamma
The previous plots had M-K reversed (phi_x=2pi/3 at the M end).
"""
import csv
import math
import os
import re

import numpy as np

from hexagonal_kcheck import (PX, PY, M_STAR, K_STAR,
                              star_distance, same_k, in_first_pc_bz)

ROOT = r"D:/document/Workbuddy/2026-11-07-22-48-25"
D = os.path.join(ROOT, "tensor_patch")
D_FULL = os.path.join(D, "eig_hexagonal_ibz_full")
D_Y = os.path.join(D, "eig_hexagonal_sym")
OUT_PNG = os.path.join(D, "hexagonal_GMK_final.png")
OUT_CSV = os.path.join(D, "hexagonal_GMK_final_junctions.csv")


def parse(path, n=12):
    if not os.path.exists(path):
        return []
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
    return out[:n]


def k_of(phi_x_deg, phi_y):
    return np.array([math.radians(phi_x_deg) / PX, phi_y / PY])


def main():
    gm = {p: parse(os.path.join(D_FULL, "GM_%d.eig" % p))
          for p in range(0, 181, 30)}
    ye = {p: parse(os.path.join(D_Y, "odd_%d.eig" % p))
          for p in range(0, 121, 30)}
    ym = {p: parse(os.path.join(D_Y, "even_%d.eig" % p))
          for p in range(0, 241, 30)}
    gm360 = parse(os.path.join(D_FULL, "GM_360.eig"))

    # Junction checks with k vectors.
    k_gm = k_of(0, 2 * math.pi)
    k_ye0 = k_of(0, 2 * math.pi)
    k_ye120 = k_of(120, 2 * math.pi)
    k_ym240 = k_of(240, 0.0)
    checks = (
        ("M", "full_GM@360", gm360, k_gm, "y_ee@0", ye[0], k_ye0),
        ("K", "y_ee@120", ye[120], k_ye120, "y_mm@240", ym[240], k_ym240),
    )
    rows = []
    for j, na, fa, ka, nb, fb, kb in checks:
        eq, reason = same_k(ka, kb)
        f1_gap = abs(fa[0] - fb[0]) if fa and fb else None
        all_gap = min((abs(x - y) for x in fa for y in fb), default=None)
        rows.append([j, na, nb, round(float(ka[0]), 5), round(float(ka[1]), 5),
                     round(float(kb[0]), 5), round(float(kb[1]), 5),
                     round(star_distance(ka, M_STAR), 5),
                     round(star_distance(ka, K_STAR), 5),
                     round(star_distance(kb, M_STAR), 5),
                     round(star_distance(kb, K_STAR), 5),
                     eq, round(f1_gap, 6) if f1_gap is not None else None,
                     round(all_gap, 6) if all_gap is not None else None,
                     "M-POINT CLOSURE" if j == "M" and eq and f1_gap < 0.02
                     else "residual remains"])
        print(j, na, "vs", nb, "same_k", eq, "f1 gap", f1_gap,
              "best all-mode gap", all_gap, flush=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["junction", "side_a", "side_b", "kA_x", "kA_y", "kB_x", "kB_y",
                    "dM_A", "dK_A", "dM_B", "dK_B", "same_k",
                    "f1_gap_GHz", "best_all_mode_gap_GHz", "verdict"])
        for r in rows:
            w.writerow(r)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8.8, 5.0), dpi=175)
        for mode, color in ((0, "#185FA5"), (1, "#d62728")):
            xs = [p / 180.0 for p in sorted(gm) if len(gm[p]) > mode]
            ys = [gm[p][mode] for p in sorted(gm) if len(gm[p]) > mode]
            ax.plot(xs, ys, "o-", ms=3.2, lw=1.4, color=color,
                    label="Gamma-M mode%d" % (mode + 1))
            xs = [1.0 + p / 120.0 for p in sorted(ye) if len(ye[p]) > mode]
            ys = [ye[p][mode] for p in sorted(ye) if len(ye[p]) > mode]
            ax.plot(xs, ys, "^-", ms=3.2, lw=1.3, color=color,
                    alpha=0.8, label="M-K y_ee mode%d" % (mode + 1))
            ps = [p for p in sorted(ym, reverse=True) if len(ym[p]) > mode]
            xs = [2.0 + (240 - p) / 240.0 for p in ps]
            ys = [ym[p][mode] for p in ps]
            ax.plot(xs, ys, "v-", ms=3.2, lw=1.3, color=color,
                    alpha=0.8, label="K-Gamma y_mm mode%d" % (mode + 1))
        for x, name in ((0, "Gamma"), (1, "M"), (2, "K"), (3, "Gamma")):
            ax.axvline(x, color="#888780", ls=":", lw=1)
        ax.set_xticks([0, 1, 2, 3])
        ax.set_xticklabels(["Gamma", "M", "K", "Gamma"])
        ax.set_xlabel("IBZ path")
        ax.set_ylabel("f (GHz)")
        ax.set_title("Gamma-M-K-Gamma with corrected M-K direction (Appendix B)")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=7, ncol=2)
        fig.tight_layout()
        fig.savefig(OUT_PNG)
        plt.close(fig)
        print("plot written", OUT_PNG, flush=True)
    except Exception as exc:
        print("plot failed", repr(exc), flush=True)


if __name__ == "__main__":
    main()
