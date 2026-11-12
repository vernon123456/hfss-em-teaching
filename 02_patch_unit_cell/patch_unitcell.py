# -*- coding: utf-8 -*-
"""Fong 2010 grounded-patch unit cell: Z(g) at 17 GHz from HFSS Eigenmode dispersion.

Model: 3 mm square unit cell, 1.57 mm eps_r=2.2 grounded substrate, square PEC
patch of side (p - g), PEC lid, four Lattice Pairs (x: px, y: 0deg).

Extraction (same method as Fong 2010, "only requires calculating the surface wave
frequency or wave vector"): fix f0 = 17 GHz, interpolate f(px) to find phi*,
beta = phi*/p, Zs = j*eta0*sqrt((beta/k0)^2 - 1).

Run:
  python patch_unitcell.py                  # full solve + post-processing
  RUN_MODE=post python patch_unitcell.py    # rebuild outputs from eig_points.csv
  MODE_INDEX=2 RUN_MODE=post ...           # pick another eigenmode branch
AEDT must run in GUI mode (non_graphical=False).
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
EIG_DIR = os.path.join(ROOT, "eig")
AEDT = os.path.join(ROOT, "patch_unitcell.aedt")
LOG = os.path.join(ROOT, "run.log")
RAW_CSV = os.path.join(ROOT, "eig_points.csv")
Z_CSV = os.path.join(ROOT, "Z_vs_g.csv")
XSM_CSV = os.path.join(ROOT, "Xs_by_mode.csv")
Z_PNG = os.path.join(ROOT, "Z_vs_g.png")
DISP_PNG = os.path.join(ROOT, "dispersion_by_g.png")

C0 = 299792458.0
ETA0 = 376.730313668
F0_GHZ = 17.0
P_MM = 3.0
H_SUB = 1.57
H_AIR = 30.0
EPS_R = 2.2
GAPS = [float(x) for x in os.environ.get(
    "GAPS_OVERRIDE", "0.2,0.4,0.6,0.8,1.0").split(",")]
PHASES = [int(x) for x in os.environ.get(
    "PHASES_OVERRIDE", "55,60,65,70,75,80,85").split(",")]
N_MODES = 6
SETUP = "Eigen1"
MODE_INDEX = int(os.environ.get("MODE_INDEX", "1"))

# Published reference points (Z in ohm, g in mm) at 17 GHz.
FONG_PTS = [(0.2, 234.0), (1.0, 161.0)]
OE_PTS = [(0.2, 245.70), (1.0, 163.38)]


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def face_map(obj, z_lo, z_hi):
    out = {}
    for face in obj.faces:
        cx, cy, cz = [float(v) for v in face.center]
        if abs(cz - z_lo) < 1e-6:
            out["bottom"] = face.id
        elif abs(cz - z_hi) < 1e-6:
            out["top"] = face.id
        elif abs(cx) < 1e-6:
            out["x0"] = face.id
        elif abs(cx - P_MM) < 1e-6:
            out["xp"] = face.id
        elif abs(cy) < 1e-6:
            out["y0"] = face.id
        elif abs(cy - P_MM) < 1e-6:
            out["yp"] = face.id
    return out


def build(app):
    app.modeler.model_units = "mm"
    app["p"] = "%smm" % P_MM
    app["g"] = "%smm" % GAPS[0]
    app["hs"] = "%smm" % H_SUB
    app["H"] = "%smm" % H_AIR
    app["px"] = "70deg"

    try:
        mat = app.materials.add_material("Sub22")
        mat.permittivity = EPS_R
    except Exception as exc:
        log("add_material variant 1 failed: %r" % exc)
        app.materials.add_material("Sub22", permittivity=EPS_R)

    sub = app.modeler.create_box([0, 0, 0], ["p", "p", "hs"],
                                 name="Substrate", material="Sub22")
    air = app.modeler.create_box([0, 0, "hs"], ["p", "p", "H"],
                                 name="Air", material="vacuum")
    patch = app.modeler.create_rectangle(2, ["g/2", "g/2", "hs"],
                                         ["p-g", "p-g"], name="Patch")

    sf = face_map(sub, 0.0, H_SUB)
    af = face_map(air, H_SUB, H_SUB + H_AIR)
    log("substrate faces=%r" % sf)
    log("air faces=%r" % af)

    app.assign_perfect_e(sf["bottom"], name="Ground")
    app.assign_perfect_e(af["top"], name="TopPEC")
    for fn in (lambda: app.assign_perfecte_to_sheets(patch.name, name="PatchPEC"),
               lambda: app.assign_perfecte_to_sheets(patch.name),
               lambda: app.assign_perfect_e(patch.name, name="PatchPEC")):
        try:
            if fn():
                break
        except Exception as exc:
            log("patch PEC variant failed: %r" % exc)

    pairs = [(sf["x0"], sf["xp"], "px", "PairSubX"),
             (af["x0"], af["xp"], "px", "PairAirX"),
             (sf["y0"], sf["yp"], "0deg", "PairSubY"),
             (af["y0"], af["yp"], "0deg", "PairAirY")]
    for fa, fb, phase, name in pairs:
        app.assign_lattice_pair([fa, fb], phase_delay="InputPhaseDelay",
                                phase_delay_param1=phase, name=name)

    setup = app.create_setup(SETUP, setup_type="HFSSEigen",
                             MinimumFrequency="10GHz", NumModes=N_MODES,
                             MaxDeltaFreq=1, MaximumPasses=10,
                             MinimumPasses=2, MinimumConvergedPasses=2)
    log("setup=%r" % setup.props)
    log("boundaries=%r" % [b.name for b in app.boundaries])
    log("solution_type=%r validate=%r" % (app.solution_type, app.validate_simple()))
    app.save_project(AEDT)
    log("project saved: %s" % AEDT)


def parse_eig(text):
    freqs, q1 = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tokens = line.split()
        if len(tokens) < 2:
            continue
        try:
            freqs.append(round(float(tokens[1]), 6))
        except ValueError:
            continue
        if q1 is None:
            try:
                q1 = float(tokens[-1])
            except ValueError:
                pass
    return freqs[:N_MODES], q1


def solve(app, gap, ph):
    app["g"] = "%smm" % gap
    app["px"] = "%ddeg" % ph
    t0 = time.time()
    app.analyze_setup(SETUP, cores=4)
    app.save_project(AEDT)
    tag = ("%s" % gap).replace(".", "p")
    path = os.path.join(EIG_DIR, "g%s_p%d.eig" % (tag, ph))
    app.odesign.GetModule("Solutions").ExportEigenmodes(
        SETUP + " : LastAdaptive", "", path)
    text = open(path, encoding="utf-8-sig", errors="ignore").read()
    freqs, q1 = parse_eig(text)
    log("g=%.1f px=%d solved %.1fs freqs=%r Q1=%r" %
        (gap, ph, time.time() - t0, freqs, q1))
    if not freqs:
        raise RuntimeError("no eigen frequencies for g=%s px=%d" % (gap, ph))
    return freqs, q1


def interp_phase(pts, f0):
    pts = sorted((f, p) for f, p in pts)
    for i in range(len(pts) - 1):
        f1, p1 = pts[i]
        f2, p2 = pts[i + 1]
        if f1 <= f0 <= f2 and f2 > f1:
            return p1 + (f0 - f1) / (f2 - f1) * (p2 - p1)
    return None


def main():
    os.makedirs(EIG_DIR, exist_ok=True)
    header = (["gap_mm", "px_deg", "beta_rad_per_m"] +
              ["f%d_GHz" % i for i in range(1, N_MODES + 1)] + ["Q1"])
    done = set()
    if os.path.exists(RAW_CSV):
        with open(RAW_CSV, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                done.add((float(row["gap_mm"]), int(row["px_deg"])))
        log("resume: %d points already solved" % len(done))
    else:
        with open(RAW_CSV, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(header)

    fresh = not os.path.exists(AEDT)
    app = Hfss(project=(AEDT if not fresh else "PatchUnitCell"),
               design="unit_cell", solution_type="Eigenmode", version="2026.1",
               non_graphical=False, new_desktop=True, close_on_exit=False)
    if "Substrate" in app.modeler.object_names:
        log("existing model detected, setups=%r" % app.setup_names)
    else:
        build(app)

    for gap in GAPS:
        for ph in PHASES:
            if (gap, ph) in done:
                continue
            freqs, q1 = solve(app, gap, ph)
            beta = math.radians(ph) / (P_MM * 1e-3)
            row = ([gap, ph, round(beta, 4)] +
                   freqs + [None] * (N_MODES - len(freqs)) + [q1])
            with open(RAW_CSV, "a", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerow(row)
            done.add((gap, ph))
    log("=== solve done, %d points ===" % len(done))
    post()


def post():
    with open(RAW_CSV, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    by_gap = {}
    for row in rows:
        by_gap.setdefault(float(row["gap_mm"]), []).append(row)
    k0 = 2.0 * math.pi * F0_GHZ * 1e9 / C0

    all_modes = {}
    for mi in range(1, N_MODES + 1):
        series = []
        for gap in sorted(by_gap):
            pts = []
            for row in by_gap[gap]:
                val = row.get("f%d_GHz" % mi)
                if val:
                    pts.append((float(val), int(row["px_deg"])))
            ph_star = interp_phase(pts, F0_GHZ)
            beta, xs = None, None
            if ph_star is not None:
                beta = math.radians(ph_star) / (P_MM * 1e-3)
                if beta > k0:
                    xs = ETA0 * math.sqrt((beta / k0) ** 2 - 1)
            series.append((gap, ph_star, beta, xs))
        all_modes[mi] = series
        vals = [s[3] for s in series if s[3] is not None]
        log("mode %d Xs range: %s" %
            (mi, "%.1f..%.1f ohm" % (min(vals), max(vals)) if vals else "n/a"))

    with open(XSM_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["mode"] + ["Xs_g%.1f_ohm" % g for g in sorted(by_gap)])
        for mi, series in all_modes.items():
            writer.writerow([mi] + [round(s[3], 3) if s[3] else "" for s in series])

    chosen = all_modes[MODE_INDEX]
    with open(Z_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["gap_mm", "phi_star_deg", "beta_rad_per_m",
                         "Xs_ohm", "Zs", "mode_index"])
        for gap, ph_star, beta, xs in chosen:
            writer.writerow([gap, round(ph_star, 3) if ph_star else "",
                             round(beta, 3) if beta else "",
                             round(xs, 3) if xs else "",
                             ("j%.3f" % xs) if xs else "", MODE_INDEX])
    log("Z_vs_g written, mode=%d" % MODE_INDEX)
    make_plots(chosen, by_gap)


def make_plots(chosen, by_gap):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        log("matplotlib unavailable: %r" % exc)
        return

    gs = [s[0] for s in chosen if s[3]]
    xs = [s[3] for s in chosen if s[3]]
    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=160)
    if gs:
        ax.plot(gs, xs, "o-", color="#d62728", lw=2, ms=6,
                label="HFSS Eigenmode, this work")
    ax.scatter([p[0] for p in FONG_PTS], [p[1] for p in FONG_PTS],
               marker="s", s=45, color="#1f77b4", label="Fong 2010 endpoints")
    ax.scatter([p[0] for p in OE_PTS], [p[1] for p in OE_PTS],
               marker="^", s=45, color="#3B6D11",
               label="Opt. Express 2015 endpoints")
    ax.set_xlabel("gap g (mm)")
    ax.set_ylabel("surface reactance Xs (ohm)")
    ax.set_title("Effective surface reactance at 17 GHz, p = 3 mm")
    ax.grid(alpha=0.3)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(Z_PNG)
    plt.close(fig)

    k0 = 2.0 * math.pi * F0_GHZ * 1e9 / C0
    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=160)
    for gap in sorted(by_gap):
        pts = sorted((float(r["beta_rad_per_m"]), float(r["f1_GHz"]))
                     for r in by_gap[gap] if r.get("f1_GHz"))
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", ms=4,
                    lw=1.4, label="g = %.1f mm" % gap)
    valid = [s[3] for s in chosen if s[3]]
    if valid:
        xbar = sum(valid) / len(valid)
        s = xbar / ETA0
        b = [300.0 + i * 25.0 for i in range(9)]
        f = [C0 * bb / (2 * math.pi * math.sqrt(1 + s * s)) / 1e9 for bb in b]
        ax.plot(b, f, "--", color="#444441", lw=1.8,
                label="ideal sheet, Xs = %.0f ohm" % xbar)
    ax.axhline(F0_GHZ, color="#888780", lw=1, ls=":")
    ax.set_xlabel("beta (rad/m)")
    ax.set_ylabel("f (GHz)")
    ax.set_title("Patch unit cell dispersion vs ideal impedance sheet")
    ax.grid(alpha=0.3)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(DISP_PNG)
    plt.close(fig)
    log("plots written: %s / %s" % (Z_PNG, DISP_PNG))


if __name__ == "__main__":
    try:
        if os.environ.get("RUN_MODE") == "post":
            post()
        else:
            main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
