# -*- coding: utf-8 -*-
"""Independent closure check: ideal impedance sheet vs the real patch unit cell.

Uses Xs = mean of the Xs(g) extracted from the patch unit cell, builds a fresh
HFSS Eigenmode model (single Impedance sheet, PEC lid, two Lattice Pairs) and
solves the same phase range. A separate HFSS-to-HFSS comparison avoids the
circular argument of extracting Xs from a single 17 GHz point and re-inserting
it into the same formula.
"""
import csv
import math
import os
import time
import traceback

os.environ.setdefault("ANSYSEM_ROOT261", r"D:\software\ANSYS Inc\v261\AnsysEM")
os.environ.setdefault("AWP_ROOT261", r"D:\software\ANSYS Inc\v261")

from ansys.aedt.core import Hfss

ROOT = r"D:\document\Workbuddy\2026-11-07-22-48-25\patch_unitcell"
Z_CSV = os.path.join(ROOT, "Z_vs_g.csv")
RAW_CSV = os.path.join(ROOT, "eig_points.csv")
AEDT = os.path.join(ROOT, "ideal_sheet.aedt")
EIG_DIR = os.path.join(ROOT, "eig_ideal")
OUT_CSV = os.path.join(ROOT, "ideal_dispersion.csv")
PNG = os.path.join(ROOT, "ideal_compare.png")
LOG = os.path.join(ROOT, "ideal_check.log")

C0 = 299792458.0
ETA0 = 376.730313668
P_MM = 3.0
W_MM = 3.0
H_MM = 60.0
PHASES = [55, 60, 65, 70, 75, 80, 85]
SETUP = "Eigen1"


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def build(app, xs):
    app.modeler.model_units = "mm"
    app["p"] = "%smm" % P_MM
    app["w"] = "%smm" % W_MM
    app["H"] = "%smm" % H_MM
    app["px"] = "70deg"
    app["Xs"] = "%.6f" % xs
    air = app.modeler.create_box([0, 0, 0], ["p", "w", "H"],
                                 name="Air", material="vacuum")
    app.modeler.create_rectangle(2, [0, 0, 0], ["p", "w"], name="ImpSheet")
    faces = {}
    for face in air.faces:
        cx, cy, cz = [float(v) for v in face.center]
        if abs(cz) < 1e-6:
            faces["bottom"] = face.id
        elif abs(cz - H_MM) < 1e-6:
            faces["top"] = face.id
        elif abs(cx) < 1e-6:
            faces["x0"] = face.id
        elif abs(cx - P_MM) < 1e-6:
            faces["xp"] = face.id
        elif abs(cy) < 1e-6:
            faces["y0"] = face.id
        elif abs(cy - W_MM) < 1e-6:
            faces["yp"] = face.id
    app.assign_impedance_to_sheet("ImpSheet", name="ImpBC",
                                  resistance=0, reactance="Xs")
    app.assign_perfect_e(faces["top"], name="PEC_Top")
    app.assign_lattice_pair([faces["x0"], faces["xp"]],
                            phase_delay="InputPhaseDelay",
                            phase_delay_param1="px", name="PairX")
    app.assign_lattice_pair([faces["y0"], faces["yp"]],
                            phase_delay="InputPhaseDelay",
                            phase_delay_param1="0deg", name="PairY")
    setup = app.create_setup(SETUP, setup_type="HFSSEigen",
                             MinimumFrequency="10GHz", NumModes=4,
                             MaxDeltaFreq=1, MaximumPasses=10,
                             MinimumPasses=2, MinimumConvergedPasses=2)
    log("setup=%r validate=%r" % (setup.props, app.validate_simple()))
    app.save_project(AEDT)


def parse_eig(text):
    freqs = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tokens = line.split()
        if len(tokens) >= 2:
            try:
                freqs.append(round(float(tokens[1]), 6))
            except ValueError:
                pass
    return freqs[:4]


def main():
    os.makedirs(EIG_DIR, exist_ok=True)
    with open(Z_CSV, encoding="utf-8") as fh:
        xs_vals = [float(r["Xs_ohm"]) for r in csv.DictReader(fh) if r["Xs_ohm"]]
    xs = sum(xs_vals) / len(xs_vals)
    log("mean Xs = %.3f ohm from %s" % (xs, xs_vals))

    app = Hfss(project="IdealSheet", design="unit_cell",
               solution_type="Eigenmode", version="2026.1",
               non_graphical=False, new_desktop=True, close_on_exit=False)
    build(app, xs)

    rows = []
    for ph in PHASES:
        app["px"] = "%ddeg" % ph
        t0 = time.time()
        app.analyze_setup(SETUP, cores=4)
        app.save_project(AEDT)
        path = os.path.join(EIG_DIR, "p%d.eig" % ph)
        app.odesign.GetModule("Solutions").ExportEigenmodes(
            SETUP + " : LastAdaptive", "", path)
        freqs = parse_eig(open(path, encoding="utf-8-sig",
                               errors="ignore").read())
        beta = math.radians(ph) / (P_MM * 1e-3)
        k0 = beta / math.sqrt(1 + (xs / ETA0) ** 2)
        f_analytic = C0 * k0 / (2 * math.pi) / 1e9
        log("px=%d solved %.1fs freqs=%r analytic=%.4f GHz" %
            (ph, time.time() - t0, freqs, f_analytic))
        rows.append([ph, round(beta, 3), freqs[0] if freqs else "",
                     round(f_analytic, 6)])

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["px_deg", "beta_rad_per_m",
                         "f_hfss_ideal_GHz", "f_analytic_GHz", "Xs_ohm"])
        for r in rows:
            writer.writerow(r + [round(xs, 3)])
    log("ideal dispersion written")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=160)
        with open(RAW_CSV, encoding="utf-8") as fh:
            patch_rows = list(csv.DictReader(fh))
        by_gap = {}
        for r in patch_rows:
            by_gap.setdefault(float(r["gap_mm"]), []).append(r)
        for gap in sorted(by_gap):
            pts = sorted((float(r["beta_rad_per_m"]), float(r["f1_GHz"]))
                         for r in by_gap[gap] if r.get("f1_GHz"))
            ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-",
                    ms=3, lw=1.2, label="patch g=%.1f mm" % gap)
        ax.plot([r[1] for r in rows if r[2]],
                [r[2] for r in rows if r[2]], "s--", color="#111111",
                lw=2, ms=6, label="ideal sheet HFSS, Xs=%.0f" % xs)
        ax.plot([r[1] for r in rows], [r[3] for r in rows],
                ":", color="#1f77b4", lw=1.5, label="ideal sheet analytic")
        ax.set_xlabel("beta (rad/m)")
        ax.set_ylabel("f (GHz)")
        ax.set_title("Patch unit cell vs ideal impedance sheet (HFSS Eigenmode)")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=8, ncol=2)
        fig.tight_layout()
        fig.savefig(PNG)
        plt.close(fig)
        log("plot written: %s" % PNG)
    except Exception as exc:
        log("plot failed: %r" % exc)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
