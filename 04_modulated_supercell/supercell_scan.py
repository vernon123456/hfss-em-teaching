# -*- coding: utf-8 -*-
"""Modulated impedance supercell: band-gap opening driven by Optimetrics.

Eight sliced-free square-patch unit cells form one supercell of length
Lambda = N*p = 24 mm. Each cell gap g_i = gmid*(1 + M*cos(2*pi*i/N)) is an
AEDT expression in the single design variable M, so Optimetrics can sweep M
together with the supercell phase phi_sup (0..180 deg) in one design.

At the folded zone boundary phi_sup = 180 deg, the two lowest folded branches
split. The split Delta f is the band gap.

Run:
  RUN_MODE=probe python supercell_scan.py   # build + one M=0 point
  python supercell_scan.py                  # full Optimetrics sweep
  RUN_MODE=export python supercell_scan.py  # re-export results only
  RUN_MODE=post python supercell_scan.py    # tables and plots only
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

ROOT = r"D:\document\Workbuddy\2026-11-07-22-48-25\tensor_patch"
AEDT = os.path.join(ROOT, "tensor_patch.aedt")
EIG_DIR = os.path.join(ROOT, "eig_supercell")
LOG = os.path.join(ROOT, "supercell.log")
OUT_CSV = os.path.join(ROOT, "supercell_results.csv")
BAND_CSV = os.path.join(ROOT, "bandgap_vs_M.csv")
DISP_PNG = os.path.join(ROOT, "dispersion_M.png")
BAND_PNG = os.path.join(ROOT, "bandgap_vs_M.png")

DESIGN = "supercell"
SETUP = "Eigen1"
PARAM_SETUP = "SweepSupercell"
N = 8
P_MM = 3.0
LAMBDA_MM = N * P_MM
H_SUB = 1.57
H_AIR = 30.0
G_MID = 0.6
M_START, M_STOP, M_STEP = 0.0, 0.3, 0.1
PHI_START, PHI_STOP, PHI_STEP = 30, 180, 30
N_MODES = 8


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def face_map(obj, z_lo, z_hi, x_len, y_len):
    out = {}
    for face in obj.faces:
        cx, cy, cz = [float(v) for v in face.center]
        if abs(cz - z_lo) < 1e-6:
            out["bottom"] = face.id
        elif abs(cz - z_hi) < 1e-6:
            out["top"] = face.id
        elif abs(cx) < 1e-6:
            out["x0"] = face.id
        elif abs(cx - x_len) < 1e-6:
            out["xp"] = face.id
        elif abs(cy) < 1e-6:
            out["y0"] = face.id
        elif abs(cy - y_len) < 1e-6:
            out["yp"] = face.id
    return out


def build(app):
    app.modeler.model_units = "mm"
    for name, value in (("p", "%smm" % P_MM), ("N", str(N)),
                        ("L", "N*p"), ("hs", "%smm" % H_SUB),
                        ("H", "%smm" % H_AIR), ("gmid", "%smm" % G_MID),
                        ("M", "0"), ("phi_sup", "90deg")):
        app[name] = value
    for i in range(N):
        c = math.cos(2.0 * math.pi * i / N)
        app["gap%d" % i] = "gmid*(1 + M*%.10f)" % c

    mat = app.materials.add_material("Sub22")
    mat.permittivity = 2.2
    sub = app.modeler.create_box([0, 0, 0], ["L", "p", "hs"],
                                 name="Substrate", material="Sub22")
    air = app.modeler.create_box([0, 0, "hs"], ["L", "p", "H"],
                                 name="Air", material="vacuum")

    sheets = []
    for i in range(N):
        x0 = "gap%d/2" % i if i == 0 else "%gmm + gap%d/2" % (i * P_MM, i)
        obj = app.modeler.create_rectangle(
            2, [x0, "gap%d/2" % i, "hs"],
            ["p - gap%d" % i, "p - gap%d" % i], name="Patch%d" % i)
        sheets.append(obj.name)
    app.assign_perfecte_to_sheets(sheets, name="PatchPEC")

    sf = face_map(sub, 0.0, H_SUB, LAMBDA_MM, P_MM)
    af = face_map(air, H_SUB, H_SUB + H_AIR, LAMBDA_MM, P_MM)
    log("substrate faces=%r air faces=%r" % (sf, af))
    app.assign_perfect_e(sf["bottom"], name="Ground")
    app.assign_perfect_e(af["top"], name="TopPEC")
    pairs = ((sf["x0"], sf["xp"], "phi_sup", "PairSubX"),
             (af["x0"], af["xp"], "phi_sup", "PairAirX"),
             (sf["y0"], sf["yp"], "0deg", "PairSubY"),
             (af["y0"], af["yp"], "0deg", "PairAirY"))
    for fa, fb, var, name in pairs:
        app.assign_lattice_pair([fa, fb], phase_delay="InputPhaseDelay",
                                phase_delay_param1=var, name=name)

    app.create_setup(SETUP, setup_type="HFSSEigen",
                     MinimumFrequency="10GHz", NumModes=N_MODES,
                     MaxDeltaFreq=1, MaximumPasses=10,
                     MinimumPasses=2, MinimumConvergedPasses=2)
    log("boundaries=%r validate=%r" %
        ([b.name for b in app.boundaries], app.validate_simple()))
    app.save_project(AEDT)


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


def create_sweep(app):
    if PARAM_SETUP in [s.name for s in app.parametrics.setups]:
        app.parametrics.delete(PARAM_SETUP)
        log("deleted stale parametric setup (discrete M data produced 0 variations)")
    setup = app.parametrics.add(
        "M", M_START, M_STOP, M_STEP, variation_type="LinearStep",
        solution=SETUP + " : LastAdaptive", name=PARAM_SETUP)
    setup.add_variation("phi_sup", PHI_START, PHI_STOP, PHI_STEP,
                        units="deg", variation_type="LinearStep")
    log("sweep props=%r" % setup.props["Sweeps"])
    return setup


def export_results(app):
    os.makedirs(EIG_DIR, exist_ok=True)
    sol = app.odesign.GetModule("Solutions")
    variations = []
    for method in ("ListVariations", "GetAvailableVariations"):
        try:
            result = getattr(sol, method)(SETUP + " : LastAdaptive")
            if result:
                variations = list(result)
                break
        except Exception as exc:
            log("%s failed: %r" % (method, exc))
    log("variations: %d" % len(variations))
    rows = []
    for idx, var in enumerate(variations):
        path = os.path.join(EIG_DIR, "var%02d.eig" % idx)
        try:
            sol.ExportEigenmodes(SETUP + " : LastAdaptive", var, path)
            freqs = parse_eig(open(path, encoding="utf-8-sig",
                                   errors="ignore").read())
        except Exception as exc:
            log("export %s failed: %r" % (var, exc))
            freqs = []
        mm = re.search(r"M='([^']+)'", var)
        pp = re.search(r"phi_sup='([^']+)'", var)
        mval = float(mm.group(1)) if mm else ""
        pval = float(pp.group(1).replace("deg", "")) if pp else ""
        row = ([var, mval, pval] + freqs +
               [None] * (N_MODES - len(freqs)))
        rows.append(row)
        log("var%02d M=%s phi=%s f1=%s" %
            (idx, mval, pval, freqs[0] if freqs else "n/a"))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["variation", "M", "phi_deg"] +
                   ["f%d_GHz" % i for i in range(1, N_MODES + 1)])
        for row in rows:
            w.writerow(row)
    log("results written: %s" % OUT_CSV)


def post():
    with open(OUT_CSV, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    data = {}
    for r in rows:
        try:
            m = float(r["M"])
            phi = float(r["phi_deg"])
        except (ValueError, TypeError):
            continue
        freqs = [float(r["f%d_GHz" % i]) for i in range(1, N_MODES + 1)
                 if r.get("f%d_GHz" % i)]
        data.setdefault(m, {})[phi] = freqs

    band = []
    with open(BAND_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["M", "phi_boundary_deg", "f1_GHz", "f2_GHz",
                    "bandgap_GHz", "bandgap_pct"])
        for m in sorted(data):
            phis = sorted(data[m])
            boundary = max(phis)
            freqs = data[m][boundary]
            if len(freqs) < 2:
                continue
            gap = freqs[1] - freqs[0]
            pct = 100.0 * gap / freqs[0]
            w.writerow([m, boundary, round(freqs[0], 6),
                        round(freqs[1], 6), round(gap, 6), round(pct, 4)])
            band.append((m, gap))
            log("M=%.3f boundary phi=%.0f gap=%.4f GHz (%.2f%%)" %
                (m, boundary, gap, pct))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        colors = ("#1f77b4", "#d62728", "#3B6D11", "#9467bd")
        fig, ax = plt.subplots(figsize=(7.4, 4.6), dpi=160)
        for ci, m in enumerate(sorted(data)):
            pts = sorted(data[m].items())
            for mode in (0, 1):
                xs = [p for p, f in pts if len(f) > mode]
                ys = [f[mode] for p, f in pts if len(f) > mode]
                ax.plot(xs, ys, "o-", ms=3, lw=1.4,
                        color=colors[ci % len(colors)],
                        label="M=%.3f mode%d" % (m, mode + 1))
        ax.axvline(180, color="#888780", ls=":", lw=1)
        ax.set_xlabel("supercell phase phi_sup (deg)")
        ax.set_ylabel("f (GHz)")
        ax.set_title("Folded dispersion of modulated 8-cell supercell")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=7, ncol=2)
        fig.tight_layout()
        fig.savefig(DISP_PNG)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(7.0, 4.2), dpi=160)
        ax.plot([b[0] for b in band], [b[1] for b in band],
                "o-", color="#d62728", lw=2, ms=7)
        ax.set_xlabel("modulation depth M")
        ax.set_ylabel("band gap at zone boundary (GHz)")
        ax.set_title("Band-gap opening vs modulation depth")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(BAND_PNG)
        plt.close(fig)
        log("plots written")
    except Exception as exc:
        log("plot failed: %r" % exc)


def main():
    mode = os.environ.get("RUN_MODE", "full")
    if mode == "post":
        post()
        return
    os.makedirs(EIG_DIR, exist_ok=True)
    lock = AEDT + ".lock"
    if os.path.exists(lock):
        os.remove(lock)
        log("removed stale lock")
    app = Hfss(project=AEDT, design=DESIGN, solution_type="Eigenmode",
               version="2026.1", non_graphical=False, new_desktop=True,
               close_on_exit=False)
    if "Substrate" not in app.modeler.object_names:
        build(app)
    else:
        log("existing supercell design detected")

    if mode == "probe":
        app["M"] = "0"
        app["phi_sup"] = "90deg"
        t0 = time.time()
        app.analyze_setup(SETUP, cores=4)
        app.save_project(AEDT)
        path = os.path.join(EIG_DIR, "probe.eig")
        sol = app.odesign.GetModule("Solutions")
        keys = list(sol.ListVariations(SETUP + " : LastAdaptive"))
        key = keys[0] if keys else ""
        log("probe variation keys=%r" % keys[:2])
        sol.ExportEigenmodes(SETUP + " : LastAdaptive", key, path)
        freqs = parse_eig(open(path, encoding="utf-8-sig",
                               errors="ignore").read())
        log("probe M=0 phi=90 solved %.1fs freqs=%r" %
            (time.time() - t0, freqs))
        return

    setup = create_sweep(app)
    if mode != "export":
        t0 = time.time()
        setup.analyze()
        log("supercell sweep done in %.1fs" % (time.time() - t0))
        app.save_project(AEDT)
    export_results(app)
    post()
    log("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
