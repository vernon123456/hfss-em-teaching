# -*- coding: utf-8 -*-
"""Reverse Fig. 13(d): find which (phi_x, phi_y) samples fold onto M.

For every already-solved spectrum point, compute the SC-frame k, reduce it
modulo the PC reciprocal lattice, and test membership in the M star (the six
60-degree images of M0). Only points on the M star are eligible for a
physical junction pairing at M.

No new HFSS run. Reuses constants from hexagonal_kcheck.py.
"""
import csv
import math
import os
import re

import numpy as np

from hexagonal_kcheck import (A, PX, PY, M0, M_STAR, K_STAR,
                              star_distance, in_first_pc_bz, same_k)

ROOT = r"D:\document\Workbuddy\2026-11-07-22-48-25\tensor_patch"
D_FULL = os.path.join(ROOT, "eig_hexagonal_ibz_full")
D_X = os.path.join(ROOT, "eig_hexagonal_symx")
D_Y = os.path.join(ROOT, "eig_hexagonal_sym")
OUT_POINTS = os.path.join(ROOT, "hexagonal_M_points.csv")
OUT_PAIRS = os.path.join(ROOT, "hexagonal_M_pairs.csv")

X_PHASES = tuple(range(0, 361, 30))
Y_PHASES = tuple(range(0, 241, 30))

# name, folder, file prefix, phases, fixed x-phase, fixed y-phase
SPECTRA = (
    ("full_GM", D_FULL, "GM", X_PHASES, 0.0, None),
    ("full_GK1", D_FULL, "GK1", Y_PHASES, None, 0.0),
    ("x_mm", D_X, "even", X_PHASES, 0.0, None),
    ("x_ee", D_X, "odd", X_PHASES, 2 * math.pi, None),
    ("x_em", D_X, "em", X_PHASES, math.pi, None),
    ("x_me", D_X, "me", X_PHASES, math.pi, None),
    ("y_mm", D_Y, "even", Y_PHASES, None, 0.0),
    ("y_ee", D_Y, "odd", Y_PHASES, None, 2 * math.pi),
)


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


def k_of(fixed_x, fixed_y, phase_deg):
    r = math.radians(phase_deg)
    if fixed_x is None:
        return np.array([r / PX, fixed_y / PY])
    return np.array([fixed_x / PX, r / PY])


def nearest_star_index(k, star):
    best = (float("inf"), -1)
    for i, s in enumerate(star):
        for m in range(-2, 3):
            for n in range(-2, 3):
                d = float(np.linalg.norm(k - s - (m * _B1 + n * _B2)))
                if d < best[0]:
                    best = (d, i)
    return best[1], best[0]


from hexagonal_kcheck import B1 as _B1, B2 as _B2  # noqa: E402


def best_freq_gap(fa, fb):
    best = None
    for x in fa:
        for y in fb:
            gap = abs(x - y)
            if best is None or gap < best[0]:
                best = (gap, x, y)
    return best


def main():
    points = []
    for name, folder, prefix, phases, fx, fy in SPECTRA:
        for p in phases:
            path = os.path.join(folder, "%s_%d.eig" % (prefix, p))
            if not os.path.exists(path):
                continue
            k = k_of(fx, fy, p)
            dm = star_distance(k, M_STAR)
            dk = star_distance(k, K_STAR)
            kbz, _ = in_first_pc_bz(k)
            freqs = parse(path)
            if dm < 1e-6:
                idx, _ = nearest_star_index(k, M_STAR)
                points.append(dict(name=name, phase=p, k=k, kbz=kbz,
                                   m_idx=idx, dk=dk, freqs=freqs))

    with open(OUT_POINTS, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["spectrum", "phase_deg", "k_x", "k_y",
                    "k_bz_x", "k_bz_y", "M_star_index",
                    "dist_to_K_star"] +
                   ["f%d_GHz" % i for i in range(1, 6)])
        for q in points:
            w.writerow([q["name"], q["phase"],
                        round(float(q["k"][0]), 5), round(float(q["k"][1]), 5),
                        round(float(q["kbz"][0]), 5), round(float(q["kbz"][1]), 5),
                        q["m_idx"], round(q["dk"], 5)] +
                       (q["freqs"][:5] + [None] * (5 - len(q["freqs"][:5]))))
    print("M-star points:", len(points), flush=True)
    for q in points:
        print("  %-10s %3d deg  k=%s  M_idx=%d  f=%s" %
              (q["name"], q["phase"], np.round(q["k"], 4), q["m_idx"],
               q["freqs"][:3]), flush=True)

    pairs = []
    for i, a in enumerate(points):
        for b in points[i + 1:]:
            if a["name"] == b["name"]:
                continue
            gap = best_freq_gap(a["freqs"], b["freqs"])
            if gap is None:
                continue
            equiv, reason = same_k(a["k"], b["k"])
            verdict = ("K-CONSISTENT MATCH (needs mode/parity confirmation)"
                       if gap[0] < 0.02 and equiv else
                       "k-consistent but frequencies differ")
            pairs.append([a["name"], a["phase"], b["name"], b["phase"],
                          round(gap[0], 6), gap[1], gap[2],
                          a["m_idx"], b["m_idx"], equiv, verdict])
    pairs.sort(key=lambda r: r[4])
    with open(OUT_PAIRS, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["spectrum_a", "phase_a_deg", "spectrum_b", "phase_b_deg",
                    "min_gap_GHz", "f_a_GHz", "f_b_GHz",
                    "M_star_index_a", "M_star_index_b",
                    "same_k_mod_lattice", "verdict"])
        for r in pairs:
            w.writerow(r)
    print("pairs:", len(pairs), flush=True)
    for r in pairs[:8]:
        print("  %-10s@%-3d vs %-10s@%-3d gap=%8.4f equiv=%s -> %s" %
              (r[0], r[1], r[2], r[3], r[4], r[9], r[10]), flush=True)
    print("wrote", OUT_POINTS, "and", OUT_PAIRS, flush=True)


if __name__ == "__main__":
    main()
