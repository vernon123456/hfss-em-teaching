# -*- coding: utf-8 -*-
"""Full IBZ phase ranges from Table IV of Jimenez-Suarez et al., IEEE TMTT 73(9), 2025.

Gamma-M : supercell Delta(phi_y) = [0, 2*pi]  -> 0..360 deg
Gamma-K1: supercell Delta(phi_x) = [0, 4*pi/3] -> 0..240 deg
Appendix B then folds Gamma-K1 branches onto the PC paths MK and K-Gamma.
"""
import csv
import math
import os
import time
import traceback

os.environ.setdefault("ANSYSEM_ROOT261", r"D:\software\ANSYS Inc\v261\AnsysEM")
os.environ.setdefault("AWP_ROOT261", r"D:\software\ANSYS Inc\v261")

from ansys.aedt.core import Hfss

import hexagonal_rect as hr
import hexagonal_ibz as ibz

ROOT = hr.ROOT
AEDT = hr.AEDT
EIG_DIR = os.path.join(ROOT, "eig_hexagonal_ibz_full")
LOG = os.path.join(ROOT, "hexagonal_ibz_full.log")
OUT_CSV = os.path.join(ROOT, "hexagonal_ibz_full.csv")
FOLD_CSV = os.path.join(ROOT, "hexagonal_ibz_folded.csv")
PATH_PNG = os.path.join(ROOT, "hexagonal_ibz_path.png")

ibz.EIG_DIR = EIG_DIR
GM_PHASES = tuple(range(0, 361, 30))
GK_PHASES = tuple(range(0, 241, 30))
N_MODES = 12


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read_eig(tag):
    path = os.path.join(EIG_DIR, tag + ".eig")
    return ibz.parse_eig(open(path, encoding="utf-8-sig",
                              errors="ignore").read())[:N_MODES]


def branch_track(by_phase, phases, anchor_idx=0):
    """Track one branch by nearest frequency from a chosen anchor mode."""
    out = {}
    prev = None
    for p in phases:
        f = by_phase.get(p, [])
        if not f:
            continue
        if prev is None:
            k = min(anchor_idx, len(f) - 1)
        else:
            k = min(range(len(f)), key=lambda i: abs(f[i] - prev))
        out[p] = f[k]
        prev = f[k]
    return out


def build_path_rows(gm_by_phase, gk_by_phase):
    """Approximate Appendix B fold. Branch IDs are heuristic (frequency continuity)."""
    rows = []
    # Gamma -> M : SC phi_y in [0,2pi] folds onto PC phi in [0,pi].
    for p in GM_PHASES:
        f = gm_by_phase.get(p, {})
        phi_pc = p if p <= 180 else 360 - p
        seg = "GM_fwd" if p <= 180 else "GM_fold"
        for mode in (1, 2):
            val = f.get(mode)
            if val is not None:
                rows.append(["GM", seg, p, phi_pc, mode, val])
    # Gamma-K1 branches: fundamental two branches -> K-Gamma, backward mode -> M-K.
    for p in GK_PHASES:
        f = gk_by_phase.get(p, {})
        for mode in (1, 2):
            val = f.get(mode)
            if val is None:
                continue
            if p <= 180:
                rows.append(["KGamma", "GK1_fwd", p, p, mode, val])
            else:
                rows.append(["KGamma", "GK1_fold", p, 360 - p, mode, val])
            if p <= 120:
                rows.append(["MK", "GK1_back", p, 120 - p, mode, val])
    return rows


def make_plot(rows):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8.0, 4.8), dpi=170)
        styles = (("GM_fwd", "#d62728", "o-"), ("GM_fold", "#d62728", "s--"),
                  ("GK1_fwd", "#185FA5", "o-"), ("GK1_fold", "#185FA5", "s--"),
                  ("GK1_back", "#3B6D11", "^--"))
        for label, color, style in styles:
            pts = [r for r in rows if r[1] == label and r[4] == 1]
            if not pts:
                continue
            xs = [r[3] for r in pts]
            ys = [r[5] for r in pts]
            ax.plot(xs, ys, style, ms=3.5, lw=1.3, color=color, label=label)
        ax.set_xlabel("folded phase (deg), per IBZ segment")
        ax.set_ylabel("f (GHz)")
        ax.set_title("Gamma-M-K-Gamma reconstruction (Appendix B fold, heuristic branches)")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=8, ncol=2)
        fig.tight_layout()
        fig.savefig(PATH_PNG)
        plt.close(fig)
        log("path plot written")
    except Exception as exc:
        log("plot failed: %r" % exc)


def main():
    os.makedirs(EIG_DIR, exist_ok=True)
    lock = AEDT + ".lock"
    if os.path.exists(lock):
        os.remove(lock)
    app = Hfss(project=AEDT, design=hr.DESIGN, solution_type="Eigenmode",
               version="2026.1", non_graphical=False, new_desktop=True,
               close_on_exit=False)
    if "Corner0" not in app.modeler.object_names:
        hr.clear_design(app)
        hr.build(app)
    ibz.ensure_setup(app)
    log("GM phases=%r GK1 phases=%r" % (GM_PHASES, GK_PHASES))

    raw = []
    for seg, var, phases in (("GM", "phi_y", GM_PHASES),
                             ("GK1", "phi_x", GK_PHASES)):
        for p in phases:
            f = ibz.solve(app, seg, var, p)
            raw.append([seg, var, p] +
                       (f[:6] + [None] * (6 - len(f[:6]))))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["segment", "swept_var", "phase_deg"] +
                   ["f%d_GHz" % i for i in range(1, 7)])
        for r in raw:
            w.writerow(r)

    gm = {r[2]: {i + 1: r[3 + i] for i in range(6)
                 if r[3 + i] is not None and r[3 + i] != ""}
          for r in raw if r[0] == "GM"}
    gk = {r[2]: {i + 1: r[3 + i] for i in range(6)
                 if r[3 + i] is not None and r[3 + i] != ""}
          for r in raw if r[0] == "GK1"}
    folded = build_path_rows(gm, gk)
    with open(FOLD_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["pc_segment", "sc_branch", "sc_phase_deg",
                    "folded_phase_deg", "mode", "f_GHz"])
        for r in folded:
            w.writerow(r)
    log("raw=%d folded_rows=%d" % (len(raw), len(folded)))
    make_plot(folded)
    app.save_project(AEDT)
    log("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
