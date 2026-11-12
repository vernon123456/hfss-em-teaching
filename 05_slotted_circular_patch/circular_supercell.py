# -*- coding: utf-8 -*-
"""8-cell supercell of slotted circular patches, compared with square-patch baseline.

Eight discs share one horizontal slot through their centres. Each disc radius
rad_i = Rmid*(1 + M*cos(2*pi*i/N)) is an expression in the design variable M,
swept together with the supercell phase phi_sup by Optimetrics.
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
EIG_DIR = os.path.join(ROOT, "eig_circular_supercell")
LOG = os.path.join(ROOT, "circular_supercell.log")
OUT_CSV = os.path.join(ROOT, "circular_supercell_results.csv")
BAND_CSV = os.path.join(ROOT, "circular_bandgap_vs_M.csv")
BAND_PNG = os.path.join(ROOT, "circular_bandgap_vs_M.png")

DESIGN = "circular_supercell"
SETUP = "Eigen1"
PARAM_SETUP = "SweepCircularSupercell"
N = 8
P_MM = 3.0
LAMBDA_MM = N * P_MM
H_SUB = 1.57
H_AIR = 30.0
R_MID = 1.2
SLOT_W = 0.3
N_MODES = 12
M_VALUES = (0.0, 0.3)
PHI_VALUES = (30, 60, 90, 120, 150, 180)


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
    for name, value in (("p", "%smm" % P_MM), ("N", str(N)), ("L", "N*p"),
                        ("hs", "%smm" % H_SUB), ("H", "%smm" % H_AIR),
                        ("Rmid", "%smm" % R_MID), ("slot_w", "%smm" % SLOT_W),
                        ("M", "0"), ("phi_sup", "90deg")):
        app[name] = value
    for i in range(N):
        c = math.cos(2.0 * math.pi * i / N)
        app["rad%d" % i] = "Rmid*(1 + M*%.10f)" % c
    mat = app.materials.add_material("Sub22")
    mat.permittivity = 2.2
    sub = app.modeler.create_box([0, 0, 0], ["L", "p", "hs"],
                                 name="Substrate", material="Sub22")
    air = app.modeler.create_box([0, 0, "hs"], ["L", "p", "H"],
                                 name="Air", material="vacuum")
    discs = []
    for i in range(N):
        obj = app.modeler.create_circle(
            2, ["%gmm" % (i * P_MM + P_MM / 2), "p/2", "hs"],
            "rad%d" % i, name="Disc%d" % i)
        discs.append(obj.name)
    app.modeler.create_rectangle(
        2, ["-p", "p/2 - slot_w/2", "hs"], ["10*p", "slot_w"], name="LongSlot")
    if not app.modeler.subtract(discs, "LongSlot", keep_originals=False):
        raise RuntimeError("slot subtraction failed")
    app.assign_perfecte_to_sheets(discs, name="PatchPEC")

    sf = face_map(sub, 0.0, H_SUB, LAMBDA_MM, P_MM)
    af = face_map(air, H_SUB, H_SUB + H_AIR, LAMBDA_MM, P_MM)
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
    log("objects=%r validate=%r" %
        (app.modeler.object_names, app.validate_simple()))
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


def main():
    os.makedirs(EIG_DIR, exist_ok=True)
    lock = AEDT + ".lock"
    if os.path.exists(lock):
        os.remove(lock)
    app = Hfss(project=AEDT, design=DESIGN, solution_type="Eigenmode",
               version="2026.1", non_graphical=False, new_desktop=True,
               close_on_exit=False)
    if "Disc0" not in app.modeler.object_names:
        build(app)
    else:
        log("existing circular supercell design detected")

    if PARAM_SETUP in [s.name for s in app.parametrics.setups]:
        app.parametrics.delete(PARAM_SETUP)
    setup = app.parametrics.add(
        "M", M_VALUES[0], M_VALUES[1], M_VALUES[1] - M_VALUES[0],
        variation_type="LinearStep",
        solution=SETUP + " : LastAdaptive", name=PARAM_SETUP)
    setup.add_variation("phi_sup", PHI_VALUES[0], PHI_VALUES[-1],
                        PHI_VALUES[1] - PHI_VALUES[0], units="deg",
                        variation_type="LinearStep")
    log("sweep props=%r" % setup.props["Sweeps"])
    sol = app.odesign.GetModule("Solutions")
    before = set(sol.ListVariations(SETUP + " : LastAdaptive"))
    t0 = time.time()
    setup.analyze()
    log("sweep solved in %.1fs" % (time.time() - t0))
    app.save_project(AEDT)
    keys = [k for k in sol.ListVariations(SETUP + " : LastAdaptive")
            if k not in before]
    log("new variations: %d" % len(keys))

    rows = []
    for idx, key in enumerate(keys):
        path = os.path.join(EIG_DIR, "var%02d.eig" % idx)
        try:
            sol.ExportEigenmodes(SETUP + " : LastAdaptive", key, path)
            freqs = parse_eig(open(path, encoding="utf-8-sig",
                                   errors="ignore").read())
        except Exception as exc:
            log("export %s failed: %r" % (key, exc))
            freqs = []
        mm = re.search(r"M='([^']+)'", key)
        pp = re.search(r"phi_sup='([^']+)'", key)
        mval = float(mm.group(1)) if mm else ""
        pval = float(pp.group(1).replace("deg", "")) if pp else ""
        rows.append([key, mval, pval] + freqs +
                    [None] * (N_MODES - len(freqs)))
        log("var%02d M=%s phi=%s f1=%s" %
            (idx, mval, pval, freqs[0] if freqs else "n/a"))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["variation", "M", "phi_deg"] +
                   ["f%d_GHz" % i for i in range(1, N_MODES + 1)])
        for r in rows:
            w.writerow(r)

    band = []
    with open(BAND_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["M", "phi_boundary_deg", "f1_GHz", "f2_GHz",
                    "bandgap_GHz"])
        for m in sorted(set(r[1] for r in rows if r[1] != "")):
            cand = [r for r in rows if r[1] == m and r[2] == 180]
            if not cand:
                continue
            freqs = [v for v in cand[0][3:] if v is not None]
            if len(freqs) < 2:
                continue
            gap = freqs[1] - freqs[0]
            w.writerow([m, 180, round(freqs[0], 6), round(freqs[1], 6),
                        round(gap, 6)])
            band.append((m, gap))
            log("M=%.2f boundary gap=%.4f GHz" % (m, gap))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7.0, 4.2), dpi=160)
        ax.plot([b[0] for b in band], [b[1] for b in band],
                "o-", color="#d62728", lw=2, ms=7,
                label="slotted circular patch supercell")
        ax.set_xlabel("modulation depth M")
        ax.set_ylabel("band gap at zone boundary (GHz)")
        ax.set_title("Circular vs square patch supercell band gap")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(BAND_PNG)
        plt.close(fig)
    except Exception as exc:
        log("plot failed: %r" % exc)
    log("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
