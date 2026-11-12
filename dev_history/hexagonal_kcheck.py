# -*- coding: utf-8 -*-
"""Check whether residual-matched frequency pairs are physically closed.

A frequency match is a physical closure only when both sides correspond to
the same crystal wavevector k (modulo a reciprocal-lattice vector, and up to
time reversal) AND that k lies on the intended high-symmetry point.

Geometry: rectangular supercell px=a, py=sqrt(3)*a. Reciprocal vectors of the
triangular PC and the rectangular SC are given in the README. M and K
coordinates follow IEEE J. Microw. 3(4) 2023 appendix A (document 10256254).
"""
import csv
import math
import os

import numpy as np

ROOT = r"D:\document\Workbuddy\2026-11-07-22-48-25\tensor_patch"
OUT = os.path.join(ROOT, "hexagonal_kcheck.csv")

A = 3.0
PX, PY = A, math.sqrt(3.0) * A
B1 = np.array([2 * math.pi / A, -2 * math.pi / (math.sqrt(3.0) * A)])
B2 = np.array([0.0, 4 * math.pi / (math.sqrt(3.0) * A)])
SC_B1 = np.array([2 * math.pi / PX, 0.0])
SC_B2 = np.array([0.0, 2 * math.pi / PY])
M0 = np.array([0.0, 2 * math.pi / (math.sqrt(3.0) * A)])
K0 = np.array([4 * math.pi / (3.0 * A), 0.0])


def rot(deg):
    t = math.radians(deg)
    return np.array([[math.cos(t), -math.sin(t)],
                     [math.sin(t), math.cos(t)]])


M_STAR = [rot(60 * k) @ M0 for k in range(6)]
K_STAR = [rot(60 * k) @ K0 for k in range(6)]


def in_first_pc_bz(k):
    """Reduce k into the PC first BZ by trying small reciprocal translations."""
    best = None
    for m in range(-3, 4):
        for n in range(-3, 4):
            cand = k + m * B1 + n * B2
            d = float(np.linalg.norm(cand))
            if best is None or d < best[0]:
                best = (d, cand, (m, n))
    return best[1], best[2]


def same_k(k1, k2, tol=1e-6):
    for m in range(-3, 4):
        for n in range(-3, 4):
            shift = m * B1 + n * B2
            if np.linalg.norm(k1 - k2 - shift) < tol:
                return True, "k1-k2 = %d*b1 + %d*b2" % (m, n)
            if np.linalg.norm(k1 + k2 - shift) < tol:
                return True, "time reversal: k1+k2 = %d*b1 + %d*b2" % (m, n)
    return False, "no integer reciprocal translation"


def star_distance(k, star):
    best = (float("inf"), None)
    for s in star:
        for m in range(-2, 3):
            for n in range(-2, 3):
                d = float(np.linalg.norm(k - s - (m * B1 + n * B2)))
                if d < best[0]:
                    best = (d, s)
    return best[0]


def k_from_phase(spectrum, phase_deg):
    """Return the SC-frame k vector for a spectrum/phase label."""
    r = math.radians(phase_deg)
    # x spectra: x phase fixed by symmetry planes; sweep phi_y.
    x_fixed = {"mm": 0.0, "ee": 2 * math.pi, "em": math.pi, "me": math.pi}
    if spectrum in x_fixed:
        return np.array([x_fixed[spectrum] / PX, r / PY])
    # y spectra: y phase fixed; sweep phi_x.
    y_fixed = {"y_even": 0.0, "y_odd": 2 * math.pi}
    if spectrum in y_fixed:
        return np.array([r / PX, y_fixed[spectrum] / PY])
    raise KeyError(spectrum)


def split_label(label):
    """Parse labels such as 'em@180', 'y_even@120', 'ee'."""
    if "@" in label:
        name, ph = label.split("@")
        return name, float(ph)
    return label, None


# (junction, side A, side B, measured frequency gap in GHz)
PAIRS = [
    ("M", "ee@180", "y_odd@120", 0.000572),
    ("M", "mm@180", "y_even@120", 2.109695),
    ("M", "em@180", "y_even@120", 0.113119),
    ("M", "me@180", "y_odd@120", 0.060107),
    ("M", "em@180", "y_odd@120", 0.166708),
    ("M", "me@180", "y_even@120", 0.219720),
    ("M", "mm@360", "y_even@120", 0.906954),
    ("K", "y_even@0", "y_even@120", 0.714387),
    ("K", "y_odd@0", "y_odd@120", 1.381020),
    ("K", "y_even@0", "y_even@180", 5.812544),
]


def main():
    rows = []
    for junction, la, lb, gap in PAIRS:
        na, pa = split_label(la)
        nb, pb = split_label(lb)
        ka = k_from_phase(na, pa)
        kb = k_from_phase(nb, pb)
        ka_r, ma = in_first_pc_bz(ka)
        kb_r, mb = in_first_pc_bz(kb)
        equiv, reason = same_k(ka, kb)
        dm_a = star_distance(ka, M_STAR)
        dm_b = star_distance(kb, M_STAR)
        dk_a = star_distance(ka, K_STAR)
        dk_b = star_distance(kb, K_STAR)
        at_m = dm_a < 1e-6 and dm_b < 1e-6
        at_k = dk_a < 1e-6 and dk_b < 1e-6
        verdict = ("PHYSICAL CLOSURE" if equiv else
                   "FREQUENCY COINCIDENCE ONLY")
        print("%-2s %-14s vs %-14s gap=%8.4f  kA=%s kB=%s equiv=%s  dM=(%.3f,%.3f) dK=(%.3f,%.3f) atM=%s atK=%s -> %s"
              % (junction, la, lb, gap,
                 np.round(ka, 4), np.round(kb, 4), equiv,
                 dm_a, dm_b, dk_a, dk_b, at_m, at_k, verdict), flush=True)
        rows.append([
            junction, la, lb, gap,
            round(float(ka[0]), 5), round(float(ka[1]), 5),
            round(float(kb[0]), 5), round(float(kb[1]), 5),
            round(float(ka_r[0]), 5), round(float(ka_r[1]), 5),
            round(float(kb_r[0]), 5), round(float(kb_r[1]), 5),
            round(dm_a, 5), round(dm_b, 5),
            round(dk_a, 5), round(dk_b, 5), equiv, at_m, at_k,
            reason, verdict])
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["junction", "side_a", "side_b", "gap_GHz",
                    "kA_x", "kA_y", "kB_x", "kB_y",
                    "kA_bz_x", "kA_bz_y", "kB_bz_x", "kB_bz_y",
                    "dist_to_M_star_A", "dist_to_M_star_B",
                    "dist_to_K_star_A", "dist_to_K_star_B",
                    "same_k_mod_lattice", "both_at_M", "both_at_K",
                    "reason", "verdict"])
        for r in rows:
            w.writerow(r)
    print("M0 =", np.round(M0, 5), " K0 =", np.round(K0, 5), flush=True)
    print("SC B1 =", np.round(SC_B1, 5), " SC B2 =", np.round(SC_B2, 5),
          flush=True)
    print("PC b1 =", np.round(B1, 5), " PC b2 =", np.round(B2, 5), flush=True)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
