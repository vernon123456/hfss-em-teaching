# -*- coding: utf-8 -*-
"""Single-point diagnostic for the hexagonal lattice blockage.

A. Phase symmetry: in a C6v lattice the two reciprocal directions
   (phi1=phi, phi2=0) and (phi1=0, phi2=phi) are equivalent, so the first
   eigenfrequencies must match. A large mismatch points at a V-vector or
   phase-sign error in the Primary/Secondary boundaries.
B. Low-phase Gamma-M tracking: sweep phi1 densely from 0 to 60 deg with
   phi2=0 and record modes 1 to 3, to see whether the 10.37 GHz point is a
   separate branch crossing mode 1. Frequency continuity is used instead of
   field plots because the Eigenmode field-export path was already shown to
   be unreliable in this workspace.
"""
import csv
import os
import re
import time
import traceback

os.environ.setdefault("ANSYSEM_ROOT261", r"D:\software\ANSYS Inc\v261\AnsysEM")
os.environ.setdefault("AWP_ROOT261", r"D:\software\ANSYS Inc\v261")

from ansys.aedt.core import Hfss

ROOT = r"D:\document\Workbuddy\2026-11-07-22-48-25\tensor_patch"
AEDT = os.path.join(ROOT, "tensor_patch.aedt")
EIG_DIR = os.path.join(ROOT, "eig_hexagonal_diag")
LOG = os.path.join(ROOT, "hexagonal_diagnose.log")
SYM_CSV = os.path.join(ROOT, "hexagonal_symmetry.csv")
LOW_CSV = os.path.join(ROOT, "hexagonal_lowphase.csv")
LOW_PNG = os.path.join(ROOT, "hexagonal_lowphase.png")

DESIGN = "hexagonal"
SETUP = "Eigen1"
SYM_CASES = ((90, 0), (0, 90), (60, 0), (0, 60))
LOW_PHASES = (0, 10, 20, 30, 40, 50, 60)


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def parse_eig(text):
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tok = line.split()
        value = None
        if len(tok) >= 2:
            try:
                value = float(tok[1])
            except ValueError:
                m = re.match(r"^\s*\d+\s+([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", line)
                if m:
                    value = float(m.group(1))
        if value is not None:
            out.append(round(value, 6))
    return out[:3]


def eigen(app, tag):
    sol = app.odesign.GetModule("Solutions")
    path = os.path.join(EIG_DIR, tag + ".eig")
    sol.ExportEigenmodes(SETUP + " : LastAdaptive", "", path)
    return parse_eig(open(path, encoding="utf-8-sig",
                          errors="ignore").read())


def solve(app, p1, p2, tag):
    app["phi1"] = "%gdeg" % p1
    app["phi2"] = "%gdeg" % p2
    t0 = time.time()
    app.analyze_setup(SETUP, cores=4)
    freqs = eigen(app, tag)
    log("phi1=%g phi2=%g solved %.1fs modes=%r" %
        (p1, p2, time.time() - t0, freqs))
    return freqs + [None] * (3 - len(freqs))


def main():
    os.makedirs(EIG_DIR, exist_ok=True)
    lock = AEDT + ".lock"
    if os.path.exists(lock):
        os.remove(lock)
    app = Hfss(project=AEDT, design=DESIGN, solution_type="Eigenmode",
               version="2026.1", non_graphical=False, new_desktop=True,
               close_on_exit=False)

    if os.environ.get("RUN_MODE") == "recheck":
        phases = [float(x) for x in os.environ.get(
            "EXTRA_PHASES", "25,30,35").split(",")]
        rows = []
        for p1 in phases:
            rows.append([p1] + solve(app, p1, 0, "recheck_%g" % p1))
        with open(os.path.join(ROOT, "hexagonal_recheck.csv"), "w",
                  newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["phi1_deg", "f1_GHz", "f2_GHz", "f3_GHz"])
            for r in rows:
                w.writerow(r)
        app.save_project(AEDT)
        log("=== recheck done ===")
        return

    sym = {}
    sym_rows = []
    for p1, p2 in SYM_CASES:
        f = solve(app, p1, p2, "sym_%d_%d" % (p1, p2))
        sym[(p1, p2)] = f
        sym_rows.append([p1, p2] + f)
    with open(SYM_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["phi1_deg", "phi2_deg", "f1_GHz", "f2_GHz", "f3_GHz"])
        for r in sym_rows:
            w.writerow(r)
    for phi in (90, 60):
        a, b = sym[(phi, 0)], sym[(0, phi)]
        if a[0] is not None and b[0] is not None:
            log("symmetry phi=%g: f1 %.4f vs %.4f, diff %.4f GHz" %
                (phi, a[0], b[0], abs(a[0] - b[0])))

    low_rows = []
    for p1 in LOW_PHASES:
        f = solve(app, p1, 0, "gm_%d" % p1)
        low_rows.append([p1] + f)
    with open(LOW_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["phi1_deg", "f1_GHz", "f2_GHz", "f3_GHz"])
        for r in low_rows:
            w.writerow(r)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=160)
        for idx, label in ((1, "mode 1"), (2, "mode 2"), (3, "mode 3")):
            xs = [r[0] for r in low_rows if r[idx] is not None]
            ys = [r[idx] for r in low_rows if r[idx] is not None]
            ax.plot(xs, ys, "o-", ms=4, lw=1.4, label=label)
        ax.set_xlabel("phi1 along a1 (deg)")
        ax.set_ylabel("f (GHz)")
        ax.set_title("Hexagonal lattice, low-phase Gamma-M branch tracking")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=9)
        fig.tight_layout()
        fig.savefig(LOW_PNG)
        plt.close(fig)
        log("plot written")
    except Exception as exc:
        log("plot failed: %r" % exc)
    app.save_project(AEDT)
    log("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
