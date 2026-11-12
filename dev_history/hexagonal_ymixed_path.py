# -*- coding: utf-8 -*-
"""High-symmetry coverage of the y-direction mixed symmetry-plane spectra.

Mixed combinations E^y_0 M^y_py/2 (em) and M^y_0 E^y_py/2 (me) fix
phi_y = pi (Fig. 15(c)(d)). For each scanned phi_x, compute the SC-frame k,
reduce modulo the PC reciprocal lattice, and label M / K / Gamma membership.
Then check whether any single mode covers M -> K -> Gamma continuously.
"""
import csv
import math
import os
import re

import numpy as np

from hexagonal_kcheck import (PX, PY, M_STAR, K_STAR,
                              star_distance, in_first_pc_bz)

ROOT = r"D:/document/Workbuddy/2026-11-07-22-48-25/tensor_patch"
D_SYM = os.path.join(ROOT, "eig_hexagonal_sym")
OUT = os.path.join(ROOT, "hexagonal_ymixed_path.csv")
OUT_SUM = os.path.join(ROOT, "hexagonal_ymixed_summary.csv")
PHASES = tuple(range(0, 241, 30))


def parse(path, n=6):
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


def main():
    rows = []
    for mode in ("em", "me"):
        for p in PHASES:
            k = np.array([math.radians(p) / PX, math.pi / PY])
            dm = star_distance(k, M_STAR)
            dk = star_distance(k, K_STAR)
            kbz, _ = in_first_pc_bz(k)
            dgamma = float(np.linalg.norm(kbz))
            tag = ("M" if dm < 1e-6 else "K" if dk < 1e-6
                   else "Gamma" if dgamma < 1e-6 else "-")
            f = parse(os.path.join(D_SYM, "%s_%d.eig" % (mode, p)))
            rows.append([mode, p, round(float(k[0]), 5), round(float(k[1]), 5),
                         round(float(kbz[0]), 5), round(float(kbz[1]), 5),
                         round(dm, 5), round(dk, 5), round(dgamma, 5), tag,
                         f[0] if f else None, f[1] if len(f) > 1 else None])
            print("%-3s phi_x=%3d k=%s dM=%.4f dK=%.4f dG=%.4f %s f1=%s" %
                  (mode, p, np.round(k, 4), dm, dk, dgamma, tag,
                   f[0] if f else None), flush=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["mode", "phi_x_deg", "k_x", "k_y", "k_bz_x", "k_bz_y",
                    "dist_M_star", "dist_K_star", "dist_Gamma",
                    "high_symmetry_point", "f1_GHz", "f2_GHz"])
        for r in rows:
            w.writerow(r)

    summary = []
    for mode in ("em", "me"):
        tags = sorted({r[9] for r in rows if r[0] == mode and r[9] != "-"})
        covers = all(t in tags for t in ("M", "K", "Gamma"))
        summary.append([mode, ",".join(tags), covers])
        print("%s visits %s, single-parity M-K-Gamma path: %s" %
              (mode, tags, covers), flush=True)
    # Reference: existing even/odd coverage (from hexagonal_K_parity_path.csv).
    ref = os.path.join(ROOT, "hexagonal_K_parity_path.csv")
    if os.path.exists(ref):
        for parity in ("even", "odd"):
            with open(ref, encoding="utf-8") as fh:
                tags = sorted({r["high_symmetry_point"] for r in csv.DictReader(fh)
                               if r["parity"] == parity
                               and r["high_symmetry_point"] != "-"})
            summary.append([parity, ",".join(tags), False])
            print("reference %s visits %s" % (parity, tags), flush=True)
    with open(OUT_SUM, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["spectrum", "high_symmetry_points", "covers_M_K_Gamma"])
        for r in summary:
            w.writerow(r)
    print("wrote", OUT, OUT_SUM, flush=True)


if __name__ == "__main__":
    main()
