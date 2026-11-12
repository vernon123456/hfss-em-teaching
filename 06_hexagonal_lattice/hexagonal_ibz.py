# -*- coding: utf-8 -*-
"""Two-segment phase scan of the rectangular supercell (Gamma-M-K-Gamma input).

Source of the phase conditions: IEEE TAP document 10980079 states for a
rectangular supercell with px=a, py=sqrt(3)a that Gamma-M is obtained with
phi_x=0, while M-K and K-Gamma can be reconstructed from the Gamma-K1 path
with phi_y=0 plus a postprocessing fold (Appendix B). Here both segments are
solved with the HFSS Eigenmode solver; the final fold is reported as an
explicit approximation, not as a strict reproduction of the paper.

Run: python hexagonal_ibz.py
"""
import csv
import math
import os
import re
import time
import traceback

os.environ.setdefault("ANSYSEM_ROOT261", r"D:\software\ANSYS Inc\v261\AnsysEM")
os.environ.setdefault("AWP_ROOT261", r"D:\software\ANSYS Inc\v261")

from ansys.aedt.core import Hfss

import hexagonal_rect as hr

ROOT = hr.ROOT
AEDT = hr.AEDT
EIG_DIR = os.path.join(ROOT, "eig_hexagonal_ibz")
LOG = os.path.join(ROOT, "hexagonal_ibz.log")
OUT_CSV = os.path.join(ROOT, "hexagonal_ibz.csv")
DEGEN_CSV = os.path.join(ROOT, "hexagonal_ibz_degeneracy.csv")
DISP_PNG = os.path.join(ROOT, "hexagonal_ibz_dispersion.png")

SETUP = "Eigen1_IBZ"
N_MODES = 12
PHASES = (0, 30, 60, 90, 120, 150, 180)
SEGMENTS = (("GM", "phi_y"), ("GK1", "phi_x"))


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
    return out[:N_MODES]


def ensure_setup(app):
    if SETUP not in app.setup_names:
        app.create_setup(SETUP, setup_type="HFSSEigen",
                         MinimumFrequency="5GHz", NumModes=N_MODES,
                         MaxDeltaFreq=1, MaximumPasses=10,
                         MinimumPasses=2, MinimumConvergedPasses=2)
        log("created %s (NumModes=%d)" % (SETUP, N_MODES))


def solve(app, seg, var, phase):
    app["phi_x"] = "0deg"
    app["phi_y"] = "0deg"
    app[var] = "%ddeg" % phase
    t0 = time.time()
    app.analyze_setup(SETUP, cores=4)
    path = os.path.join(EIG_DIR, "%s_%d.eig" % (seg, phase))
    app.odesign.GetModule("Solutions").ExportEigenmodes(
        SETUP + " : LastAdaptive", "", path)
    freqs = parse_eig(open(path, encoding="utf-8-sig",
                           errors="ignore").read())
    log("%s %s=%d solved %.1fs modes=%r" %
        (seg, var, phase, time.time() - t0, freqs[:4]))
    return freqs


def degeneracy_pairs(freqs, tol=0.02):
    return [(i + 1, freqs[i], freqs[i + 1], freqs[i + 1] - freqs[i])
            for i in range(len(freqs) - 1)
            if 0 <= freqs[i + 1] - freqs[i] < tol]


def make_plot(rows):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7.6, 4.6), dpi=160)
        for seg, color in (("GM", "#d62728"), ("GK1", "#185FA5")):
            pts = [r for r in rows if r[0] == seg]
            xs = [r[2] for r in pts]
            for idx in range(4):
                ys = [r[4 + idx] for r in pts
                      if r[4 + idx] is not None and r[4 + idx] != ""]
                if not ys:
                    continue
                ax.plot(xs[:len(ys)], ys, "o-", ms=3.5, lw=1.3,
                        color=color,
                        label="%s mode%d" % (seg, idx + 1) if idx < 2 else None)
        ax.set_xlabel("phase (deg),  phi_y for Gamma-M,  phi_x for Gamma-K1")
        ax.set_ylabel("f (GHz)")
        ax.set_title("Rectangular supercell, two IBZ phase segments")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()
        fig.savefig(DISP_PNG)
        plt.close(fig)
        log("plot written")
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
        log("rebuilt rectangular supercell geometry")
    else:
        log("existing rectangular supercell detected")
    ensure_setup(app)

    rows = []
    degens = []
    for seg, var in SEGMENTS:
        for phase in PHASES:
            freqs = solve(app, seg, var, phase)
            rows.append([seg, var, phase] +
                        (freqs[:6] + [None] * (6 - len(freqs[:6]))))
            for m1, f1, f2, gap in degeneracy_pairs(freqs):
                degens.append([seg, phase, m1, m1 + 1, f1, f2, round(gap, 6)])
                log("degenerate %s phase=%d modes %d/%d gap=%.6f GHz" %
                    (seg, phase, m1, m1 + 1, gap))

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["segment", "swept_var", "phase_deg"] +
                   ["f%d_GHz" % i for i in range(1, 7)])
        for r in rows:
            w.writerow(r)
    with open(DEGEN_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["segment", "phase_deg", "mode_a", "mode_b",
                    "f_a_GHz", "f_b_GHz", "gap_GHz"])
        for r in degens:
            w.writerow(r)
    log("rows=%d degenerate_pairs=%d" % (len(rows), len(degens)))
    make_plot(rows)
    app.save_project(AEDT)
    log("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
