# -*- coding: utf-8 -*-
"""Locate M and K on the Gamma-K1 path, then rebuild junction residuals.

Appendix B (IEEE TMTT 73(9), 2025): the SC path Gamma-K1 has
phi_x in [0, 4*pi/3] with phi_y = 0 (or 2*pi under E-E planes). The
fundamental two branches correspond to the PC path Gamma-K; the backward
mode over 2*pi/3 >= phi_x >= 0 corresponds to KM. This script checks which
(phi_y condition, phi_x) samples actually fold onto M or K, then pairs
the Gamma-M endpoint with the M-K start, and the M-K end with K-Gamma.

No new HFSS run.
"""
import csv
import math
import os
import re

import numpy as np

from hexagonal_kcheck import (PX, PY, M_STAR, K_STAR, M0, K0,
                              star_distance, in_first_pc_bz, same_k)

ROOT = r"D:\document\Workbuddy\2026-11-07-22-48-25\tensor_patch"
D_Y = os.path.join(ROOT, "eig_hexagonal_sym")
D_FULL = os.path.join(ROOT, "eig_hexagonal_ibz_full")
D_X = os.path.join(ROOT, "eig_hexagonal_symx")
OUT_FOLD = os.path.join(ROOT, "hexagonal_path_fold.csv")
OUT_JUNC = os.path.join(ROOT, "hexagonal_path_junctions.csv")

PHASES = tuple(range(0, 241, 30))
COND = (("y_mm", "even", 0.0), ("y_ee", "odd", 2 * math.pi))


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


def best_gap(fa, fb):
    best = None
    for x in fa:
        for y in fb:
            g = abs(x - y)
            if best is None or g < best[0]:
                best = (g, x, y)
    return best


def main():
    fold = []
    for name, prefix, phi_y in COND:
        for p in PHASES:
            k = k_of(p, phi_y)
            dm = star_distance(k, M_STAR)
            dk = star_distance(k, K_STAR)
            kbz, _ = in_first_pc_bz(k)
            f = parse(os.path.join(D_Y, "%s_%d.eig" % (prefix, p)))
            tag = ("M" if dm < 1e-6 else "K" if dk < 1e-6 else "-")
            fold.append(dict(name=name, p=p, k=k, kbz=kbz, dm=dm, dk=dk,
                             tag=tag, freqs=f))
            print("%-5s phi_x=%3d  k=%s  dM=%.4f dK=%.4f  %s  f1=%s" %
                  (name, p, np.round(k, 4), dm, dk, tag,
                   f[0] if f else None), flush=True)
    with open(OUT_FOLD, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["spectrum", "phi_x_deg", "k_x", "k_y", "k_bz_x", "k_bz_y",
                    "dist_M_star", "dist_K_star", "on_star", "f1_GHz"])
        for q in fold:
            w.writerow([q["name"], q["p"],
                        round(float(q["k"][0]), 5), round(float(q["k"][1]), 5),
                        round(float(q["kbz"][0]), 5), round(float(q["kbz"][1]), 5),
                        round(q["dm"], 5), round(q["dk"], 5), q["tag"],
                        q["freqs"][0] if q["freqs"] else None])

    # Gamma-M endpoint: full supercell at phi_y=2pi (k = M0).
    gm_end = parse(os.path.join(D_FULL, "GM_360.eig"))
    gm_k = np.array([0.0, 2 * math.pi / PY])
    # M-K start: Gamma-K1 samples on the M star.
    m_starts = [q for q in fold if q["tag"] == "M"]
    # K-Gamma start: Gamma-K1 samples on the K star.
    k_starts = [q for q in fold if q["tag"] == "K"]

    rows = []
    for q in m_starts:
        g = best_gap(gm_end, q["freqs"])
        eq, reason = same_k(gm_k, q["k"])
        rows.append(["M", "full_GM@360", "%s@%d" % (q["name"], q["p"]),
                     round(g[0], 6) if g else None,
                     g[1] if g else None, g[2] if g else None,
                     eq, reason,
                     "M-POINT CLOSURE" if g and g[0] < 0.02 and eq
                     else "k mismatch or frequency gap"])
    # M-K end to K-Gamma start, both on K star: compare distinct samples.
    for a in k_starts:
        for b in k_starts:
            if a is b:
                continue
            g = best_gap(a["freqs"], b["freqs"])
            eq, reason = same_k(a["k"], b["k"])
            rows.append(["K", "%s@%d" % (a["name"], a["p"]),
                         "%s@%d" % (b["name"], b["p"]),
                         round(g[0], 6) if g else None,
                         g[1] if g else None, g[2] if g else None,
                         eq, reason,
                         "K-POINT CLOSURE" if g and g[0] < 0.02 and eq
                         else "k mismatch or frequency gap"])
    with open(OUT_JUNC, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["junction", "side_a", "side_b", "min_gap_GHz",
                    "f_a_GHz", "f_b_GHz", "same_k", "reason", "verdict"])
        for r in rows:
            w.writerow(r)
    print("--- junctions ---", flush=True)
    for r in rows:
        print("  %s %-16s vs %-16s gap=%s eq=%s -> %s" %
              (r[0], r[1], r[2], r[3], r[6], r[8]), flush=True)
    print("M0 =", np.round(M0, 5), "K0 =", np.round(K0, 5), flush=True)
    print("wrote", OUT_FOLD, OUT_JUNC, flush=True)


if __name__ == "__main__":
    main()
