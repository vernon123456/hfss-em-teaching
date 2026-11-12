# -*- coding: utf-8 -*-
"""Single-design parametric sliced patch driven by Optimetrics.

theta_s and gs are AEDT design variables. A relative coordinate system at the
cell centre plus oEditor.Rotate with RotateAngle="theta_s" rotates the slot;
modeler.subtract cuts the slot out of the patch sheet. phix/phiy remain design
variables for the four Lattice Pairs.

An Optimetrics Parametric setup sweeps theta_s and gs, solves every variation,
and exports the eigenmode tables.

Run:
  python parametric_scan.py
  RUN_MODE=export python parametric_scan.py   # re-export results only
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
EIG_DIR = os.path.join(ROOT, "eig_parametric")
LOG = os.path.join(ROOT, "parametric.log")
OUT_CSV = os.path.join(ROOT, "parametric_results.csv")
SWEEP_CSV = os.path.join(ROOT, "parametric_export.csv")

DESIGN = "parametric"
SETUP = "Eigen1"
PARAM_SETUP = "SweepVars"
THETA_S_VALUES = "0deg 45deg 90deg"
GS_VALUES = "0.2mm 1mm"
N_MODES = 6


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def face_map(obj, z_lo, z_hi, p):
    out = {}
    for face in obj.faces:
        cx, cy, cz = [float(v) for v in face.center]
        if abs(cz - z_lo) < 1e-6:
            out["bottom"] = face.id
        elif abs(cz - z_hi) < 1e-6:
            out["top"] = face.id
        elif abs(cx) < 1e-6:
            out["x0"] = face.id
        elif abs(cx - p) < 1e-6:
            out["xp"] = face.id
        elif abs(cy) < 1e-6:
            out["y0"] = face.id
        elif abs(cy - p) < 1e-6:
            out["yp"] = face.id
    return out


def build(app):
    app.modeler.model_units = "mm"
    variables = (("p", "3mm"), ("g", "0.2mm"), ("hs", "1.57mm"),
                 ("H", "30mm"), ("gs", "1mm"), ("theta_s", "45deg"),
                 ("phix", "70deg"), ("phiy", "0deg"))
    for name, value in variables:
        app[name] = value
    mat = app.materials.add_material("Sub22")
    mat.permittivity = 2.2
    sub = app.modeler.create_box([0, 0, 0], ["p", "p", "hs"],
                                 name="Substrate", material="Sub22")
    air = app.modeler.create_box([0, 0, "hs"], ["p", "p", "H"],
                                 name="Air", material="vacuum")
    app.modeler.create_rectangle(2, ["g/2", "g/2", "hs"],
                                 ["p-g", "p-g"], name="Patch")
    app.modeler.create_rectangle(2, ["p/2 - p", "p/2 - gs/2", "hs"],
                                 ["2*p", "gs"], name="Slot")

    o = app.oeditor
    o.CreateRelativeCS(
        ["NAME:RelativeCSParameters", "Mode:=", "Axis/Position",
         "OriginX:=", "p/2", "OriginY:=", "p/2", "OriginZ:=", "hs",
         "XAxisXvec:=", "1mm", "XAxisYvec:=", "0mm", "XAxisZvec:=", "0mm",
         "YAxisXvec:=", "0mm", "YAxisYvec:=", "1mm", "YAxisZvec:=", "0mm"],
        ["NAME:Attributes", "Name:=", "CS_center"])
    o.Rotate(
        ["NAME:Selections", "Selections:=", "Slot",
         "NewPartsModelFlag:=", "Model"],
        ["NAME:RotateParameters", "RotateAxis:=", "Z",
         "RotateAngle:=", "theta_s", "CoordinateSystem:=", "CS_center"])
    if not app.modeler.subtract("Patch", "Slot", keep_originals=False):
        raise RuntimeError("slot subtraction failed")
    app.assign_perfecte_to_sheets("Patch", name="PatchPEC")
    log("parametric geometry built, objects=%r" % app.modeler.object_names)

    sf = face_map(sub, 0.0, 1.57, 3.0)
    af = face_map(air, 1.57, 31.57, 3.0)
    app.assign_perfect_e(sf["bottom"], name="Ground")
    app.assign_perfect_e(af["top"], name="TopPEC")
    pairs = ((sf["x0"], sf["xp"], "phix", "PairSubX"),
             (af["x0"], af["xp"], "phix", "PairAirX"),
             (sf["y0"], sf["yp"], "phiy", "PairSubY"),
             (af["y0"], af["yp"], "phiy", "PairAirY"))
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


def variations_of(app):
    sol = app.odesign.GetModule("Solutions")
    for method in ("ListVariations", "GetAvailableVariations", "GetVariations"):
        try:
            result = getattr(sol, method)(SETUP + " : LastAdaptive")
            if result:
                log("variations via %s: %r" % (method, result))
                return list(result)
        except Exception as exc:
            log("%s failed: %r" % (method, exc))
    return []


def export_results(app):
    os.makedirs(EIG_DIR, exist_ok=True)
    variations = variations_of(app)
    rows = []
    for idx, var in enumerate(variations):
        path = os.path.join(EIG_DIR, "var%d.eig" % idx)
        try:
            app.odesign.GetModule("Solutions").ExportEigenmodes(
                SETUP + " : LastAdaptive", var, path)
            freqs = parse_eig(open(path, encoding="utf-8-sig",
                                   errors="ignore").read())
        except Exception as exc:
            log("export %s failed: %r" % (var, exc))
            freqs = []
        rows.append([var] + freqs + [None] * (N_MODES - len(freqs)))
        log("var%d %s freqs=%r" % (idx, var, freqs))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["variation"] + ["f%d_GHz" % i for i in range(1, N_MODES + 1)])
        for row in rows:
            w.writerow(row)
    try:
        app.export_parametric_results(PARAM_SETUP, SWEEP_CSV)
        log("parametric export written: %s" % SWEEP_CSV)
    except Exception as exc:
        log("export_parametric_results failed: %r" % exc)


def main():
    os.makedirs(EIG_DIR, exist_ok=True)
    lock = AEDT + ".lock"
    if os.path.exists(lock):
        os.remove(lock)
        log("removed stale lock")
    app = Hfss(project=AEDT, design=DESIGN, solution_type="Eigenmode",
               version="2026.1", non_graphical=False, new_desktop=True,
               close_on_exit=False)
    if "Patch" not in app.modeler.object_names:
        build(app)
    else:
        log("existing parametric design detected")

    if PARAM_SETUP not in [s.name for s in app.parametrics.setups]:
        setup = app.parametrics.add(
            "theta_s", 0, 90, 45, variation_type="LinearStep",
            solution=SETUP + " : LastAdaptive", name=PARAM_SETUP)
        setup.add_variation("gs", 0.2, 1.0, 0.8, units="mm",
                            variation_type="LinearStep")
        setup.auto_update = True
        log("parametric setup props=%r" % setup.props)
    else:
        setup = next(s for s in app.parametrics.setups if s.name == PARAM_SETUP)

    if os.environ.get("RUN_MODE") != "export":
        t0 = time.time()
        setup.analyze()
        log("parametric solve done in %.1fs" % (time.time() - t0))
        app.save_project(AEDT)
    export_results(app)
    log("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
