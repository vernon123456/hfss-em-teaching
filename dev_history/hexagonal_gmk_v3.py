# -*- coding: utf-8 -*-
"""Six parity/phase-condition spectra and junction residuals.

x-direction spectra (sweep phi_y 0..2pi, x phase fixed by symmetry planes):
  mm  M^x_0 M^x_px/2 -> phi_x = 0
  ee  E^x_0 E^x_px/2 -> phi_x = 2*pi
  em  E^x_0 M^x_px/2 -> phi_x = pi
  me  M^x_0 E^x_px/2 -> phi_x = pi
y-direction spectra (sweep phi_x 0..4pi/3, y phase fixed):
  mm / ee from the earlier half supercell.

Residuals are frequency gaps between adjacent path segments at M and K.
Branch-to-path assignment remains heuristic; labels are strict.
"""
import csv
import os
import re

ROOT = r"D:\document\Workbuddy\2026-11-07-22-48-25\tensor_patch"
DIR_X = os.path.join(ROOT, "eig_hexagonal_symx")
DIR_Y = os.path.join(ROOT, "eig_hexagonal_sym")
DIR_FULL = os.path.join(ROOT, "eig_hexagonal_ibz_full")
OUT_MODES = os.path.join(ROOT, "hexagonal_sixspectra_modes.csv")
OUT_RES = os.path.join(ROOT, "hexagonal_sixspectra_residual.csv")
OUT_PNG = os.path.join(ROOT, "hexagonal_GMK_six.png")

X_PHASES = tuple(range(0, 361, 30))
Y_PHASES = tuple(range(0, 241, 30))
COND = {"mm": "phi_x=0", "ee": "phi_x=2pi",
        "em": "phi_x=pi", "me": "phi_x=pi",
        "y_even": "phi_y=0", "y_odd": "phi_y=2pi"}


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


def nums(vals):
    return [v for v in vals if v is not None]


def best_cross(a_sets, b_sets):
    """Best frequency match between two collections of (label, freqs)."""
    best = None
    for la, a in a_sets:
        for x in nums(a):
            for lb, b in b_sets:
                for y in nums(b):
                    gap = abs(x - y)
                    if best is None or gap < best[0]:
                        best = (gap, la, lb, x, y)
    return best


def main():
    x = {m: load(DIR_X, prefix, X_PHASES)
         for m, prefix in (("mm", "even"), ("ee", "odd"),
                           ("em", "em"), ("me", "me"))}
    y = {"y_even": load(DIR_Y, "even", Y_PHASES),
         "y_odd": load(DIR_Y, "odd", Y_PHASES)}
    gm = load(DIR_FULL, "GM", X_PHASES)
    gk = load(DIR_FULL, "GK1", Y_PHASES)

    with open(OUT_MODES, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["spectrum", "phase_condition", "phase_deg"] +
                   ["f%d_GHz" % i for i in range(1, 7)])
        for name, data in list(x.items()) + list(y.items()) + [
                ("full_GM", gm), ("full_GK1", gk)]:
            cond = COND.get(name, "periodic")
            for p in sorted(data):
                w.writerow([name, cond, p] + data[p])

    # M junction: Gamma-M end (x spectra at phi_y=180 or 360) against
    # M-K start (y spectra at phi_x=120).
    m_a = [(m, x[m][180]) for m in x] + [(m + "@360", x[m][360]) for m in x]
    m_b = [(k, y[k][120]) for k in y]
    # K junction: M-K end (y at phi_x=0) against K-Gamma start (y at 120/180).
    k_a = [(k, y[k][0]) for k in y]
    k_b = [(k + "@180", y[k][180]) for k in y] + [
        (k + "@120", y[k][120]) for k in y]

    res = []
    for label, a, b in (("M", m_a, m_b), ("K", k_a, k_b)):
        best = best_cross(a, b)
        if best:
            res.append([label, round(best[0], 6), best[1], best[2],
                        best[3], best[4]])
            print(label, "best residual", round(best[0], 6), "GHz",
                  best[1], "vs", best[2], flush=True)
    # Same-condition pairs for reference.
    for m in x:
        for k in y:
            pair = best_cross([(m + "@180", x[m][180])], [(k, y[k][120])])
            if pair:
                res.append(["M " + m + "/" + k, round(pair[0], 6),
                            pair[1], pair[2], pair[3], pair[4]])
    with open(OUT_RES, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["junction", "min_gap_GHz", "side_a", "side_b",
                    "f_a_GHz", "f_b_GHz"])
        for r in res:
            w.writerow(r)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8.8, 5.0), dpi=175)
        colors = {"mm": "#185FA5", "ee": "#d62728",
                  "em": "#3B6D11", "me": "#9467bd"}
        for m, data in x.items():
            xs = [p / 180.0 for p in X_PHASES
                  if p <= 180 and data[p][0] is not None]
            ys = [data[p][0] for p in X_PHASES
                  if p <= 180 and data[p][0] is not None]
            ax.plot(xs, ys, "o-", ms=3.2, lw=1.3, color=colors[m],
                    label="Gamma-M %s (%s)" % (m, COND[m]))
        for k, data in y.items():
            pts = [(1.0 + (120 - p) / 120.0, data[p][0]) for p in Y_PHASES
                   if p <= 120 and data[p][0] is not None]
            ax.plot([q[0] for q in pts], [q[1] for q in pts], "^--",
                    ms=3.2, lw=1.1, color="#ff7f0e" if k == "y_odd" else "#17becf",
                    alpha=0.8, label="M-K %s" % k)
            pts2 = [(2.0 + (180 - p) / 180.0, data[p][0]) for p in Y_PHASES
                    if p <= 180 and data[p][0] is not None]
            ax.plot([q[0] for q in pts2], [q[1] for q in pts2], "v--",
                    ms=3.2, lw=1.1, color="#ff7f0e" if k == "y_odd" else "#17becf",
                    alpha=0.8, label="K-Gamma %s" % k)
        for xpos, name in ((0, "Gamma"), (1, "M"), (2, "K"), (3, "Gamma")):
            ax.axvline(xpos, color="#888780", ls=":", lw=1)
        ax.set_xticks([0, 1, 2, 3])
        ax.set_xticklabels(["Gamma", "M", "K", "Gamma"])
        ax.set_xlabel("IBZ path")
        ax.set_ylabel("f (GHz)")
        ax.set_title("Six symmetry-plane spectra (branch assignment heuristic)")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=6.8, ncol=2)
        fig.tight_layout()
        fig.savefig(OUT_PNG)
        plt.close(fig)
        print("plot written", OUT_PNG, flush=True)
    except Exception as exc:
        print("plot failed", repr(exc), flush=True)

    print("Gamma phi_y=0:", {m: x[m][0][:2] for m in x}, flush=True)


if __name__ == "__main__":
    main()
