# -*- coding: utf-8 -*-
"""K-point parity correspondence: is the 2.49 GHz gap a mode mismatch?

Available spectra at K:
  full_GK1@240  : k = K0, no symmetry plane (all parities)
  y_mm@240      : M^y_0 M^y_py/2, PMC/PMC -> even modes
  y_ee@120      : E^y_0 E^y_py/2, PEC/PEC -> odd modes
Match each parity branch to the full-supercell mode index by frequency.
Then check whether a single parity offers a continuous M -> K -> Gamma path.
"""
import csv
import math
import os
import re

import numpy as np

from hexagonal_kcheck import (PX, PY, M_STAR, K_STAR,
                              star_distance, in_first_pc_bz)

ROOT = r"D:/document/Workbuddy/2026-11-07-22-48-25/tensor_patch"
D_FULL = os.path.join(ROOT, "eig_hexagonal_ibz_full")
D_Y = os.path.join(ROOT, "eig_hexagonal_sym")
OUT = os.path.join(ROOT, "hexagonal_K_parity.csv")
OUT_PATH = os.path.join(ROOT, "hexagonal_K_parity_path.csv")


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


def nearest(f, ref):
    best = None
    for i, r in enumerate(ref):
        g = abs(f - r)
        if best is None or g < best[0]:
            best = (g, i + 1, r)
    return best


def k_of(phi_x_deg, phi_y):
    return np.array([math.radians(phi_x_deg) / PX, phi_y / PY])


def main():
    full = parse(os.path.join(D_FULL, "GK1_240.eig"))
    even = parse(os.path.join(D_Y, "even_240.eig"))
    odd = parse(os.path.join(D_Y, "odd_120.eig"))
    print("full supercell at K0:", full[:5], flush=True)
    rows = []
    for parity, freqs, k in (("even (M-M PMC)", even, k_of(240, 0.0)),
                             ("odd (E-E PEC)", odd, k_of(120, 2 * math.pi))):
        for j, f in enumerate(freqs[:5]):
            g, idx, ref = nearest(f, full)
            rows.append([parity, j + 1, f, idx, ref, round(g, 6),
                         round(star_distance(k, K_STAR), 6)])
            print("%-16s mode%d f=%9.4f -> full mode%d %9.4f (gap %.4f)" %
                  (parity, j + 1, f, idx, ref, g), flush=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["parity", "branch", "f_GHz", "full_supercell_mode",
                    "full_f_GHz", "gap_GHz", "dist_to_K_star"])
        for r in rows:
            w.writerow(r)

    # Which high-symmetry points does each y spectrum pass through?
    path_rows = []
    for parity, prefix, phi_y in (("even", "even", 0.0),
                                  ("odd", "odd", 2 * math.pi)):
        for p in range(0, 241, 30):
            k = k_of(p, phi_y)
            dm = star_distance(k, M_STAR)
            dk = star_distance(k, K_STAR)
            kbz, _ = in_first_pc_bz(k)
            tag = ("M" if dm < 1e-6 else "K" if dk < 1e-6
                   else "Gamma" if np.linalg.norm(kbz) < 1e-6 else "-")
            path_rows.append([parity, p, round(float(k[0]), 5),
                              round(float(k[1]), 5),
                              round(float(kbz[0]), 5), round(float(kbz[1]), 5),
                              round(dm, 5), round(dk, 5), tag])
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["parity", "phi_x_deg", "k_x", "k_y", "k_bz_x", "k_bz_y",
                    "dist_M_star", "dist_K_star", "high_symmetry_point"])
        for r in path_rows:
            w.writerow(r)

    for parity in ("even", "odd"):
        tags = sorted({r[8] for r in path_rows if r[0] == parity})
        print("%s y-spectrum visits: %s" % (parity, tags), flush=True)

    even_first = even[0] if even else None
    odd_first = odd[0] if odd else None
    if even_first and odd_first:
        print("K f1 gap between even and odd lowest branches: %.6f GHz" %
              abs(even_first - odd_first), flush=True)
    print("wrote", OUT, OUT_PATH, flush=True)


if __name__ == "__main__":
    main()
