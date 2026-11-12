# -*- coding: utf-8 -*-
"""Independent closure: ideal Anisotropic Impedance sheet built from the fitted tensor.

Reads Xxx/Xxy/Xyy from tensor_fit.csv, builds a fresh HFSS Eigenmode model with
an anisotropic impedance boundary, and solves one phase point per propagation
direction. The phase is chosen so the fitted tensor predicts f = 17 GHz; a
matching HFSS frequency is an independent check across two different models.
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
FIT_CSV = os.path.join(ROOT, "tensor_fit.csv")
RAW_CSV = os.path.join(ROOT, "eig_points.csv")
XEFF_CSV = os.path.join(ROOT, "Xeff_by_angle.csv")
AEDT = os.path.join(ROOT, "ideal_tensor.aedt")
EIG_DIR = os.path.join(ROOT, "eig_ideal")
OUT_CSV = os.path.join(ROOT, "ideal_tensor_compare.csv")
PNG = os.path.join(ROOT, "ideal_tensor_compare.png")
LOG = os.path.join(ROOT, "ideal_check.log")

C0 = 299792458.0
ETA0 = 376.730313668
F0_GHZ = 17.0
P_MM = 3.0
W_MM = 3.0
H_MM = 60.0
SETUP = "Eigen1"


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def build(app, xxx, xxy, xyy):
    app.modeler.model_units = "mm"
    app["p"] = "%smm" % P_MM
    app["w"] = "%smm" % W_MM
    app["H"] = "%smm" % H_MM
    app["phix"] = "70deg"
    app["phiy"] = "0deg"
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
    app.assign_impedance_to_sheet(
        "ImpSheet", name="TensorBC",
        resistance=[0, 0, 0, 0],
        reactance=[round(xxx, 4), round(xxy, 4),
                   round(xxy, 4), round(xyy, 4)])
    app.assign_perfect_e(faces["top"], name="PEC_Top")
    app.assign_lattice_pair([faces["x0"], faces["xp"]],
                            phase_delay="InputPhaseDelay",
                            phase_delay_param1="phix", name="PairX")
    app.assign_lattice_pair([faces["y0"], faces["yp"]],
                            phase_delay="InputPhaseDelay",
                            phase_delay_param1="phiy", name="PairY")
    app.create_setup(SETUP, setup_type="HFSSEigen",
                     MinimumFrequency="10GHz", NumModes=4,
                     MaxDeltaFreq=1, MaximumPasses=10,
                     MinimumPasses=2, MinimumConvergedPasses=2)
    log("ideal tensor BC: Xxx=%.3f Xxy=%.3f Xyy=%.3f validate=%r" %
        (xxx, xxy, xyy, app.validate_simple()))
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
                # HFSS may concatenate the frequency and a tiny imaginary part
                m = re.match(r"^\s*\d+\s+([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", line)
                if m:
                    value = float(m.group(1))
        if value is not None:
            out.append(value)
    return out[:4]


def main():
    os.makedirs(EIG_DIR, exist_ok=True)
    with open(FIT_CSV, encoding="utf-8") as fh:
        fits = list(csv.DictReader(fh))
    target = os.environ.get("TARGET_CFG", "ts45_gs10")
    row = next((r for r in fits if r["cfg"] == target), None)
    if row is None:
        raise RuntimeError("no fit row for %s" % target)
    xxx, xxy, xyy = (float(row["Xxx_ohm"]), float(row["Xxy_ohm"]),
                     float(row["Xyy_ohm"]))
    with open(XEFF_CSV, encoding="utf-8") as fh:
        xeff = [r for r in csv.DictReader(fh) if r["cfg"] == target]

    lock = AEDT + ".lock"
    if os.path.exists(lock):
        os.remove(lock)
        log("removed stale lock")
    fresh = not os.path.exists(AEDT)
    app = Hfss(project=(AEDT if not fresh else "IdealTensor"),
               design="ideal_tensor", solution_type="Eigenmode",
               version="2026.1", non_graphical=False,
               new_desktop=True, close_on_exit=False)
    build(app, xxx, xxy, xyy)

    k0 = 2.0 * math.pi * F0_GHZ * 1e9 / C0
    rows = []
    for r in sorted(xeff, key=lambda x: float(x["theta_k_deg"])):
        tk = float(r["theta_k_deg"])
        xs = float(r["Xeff_ohm"])
        beta = k0 * math.sqrt(1 + (xs / ETA0) ** 2)
        amp = math.degrees(beta * P_MM * 1e-3)
        phix = amp * math.cos(math.radians(tk))
        phiy = amp * math.sin(math.radians(tk))
        path = os.path.join(EIG_DIR, "tk%s.eig" % ("%g" % tk).replace(".", "p"))
        t0 = time.time()
        if os.path.exists(path):
            log("reuse existing %s" % os.path.basename(path))
        else:
            app["phix"] = "%.6fdeg" % phix
            app["phiy"] = "%.6fdeg" % phiy
            app.analyze_setup(SETUP, cores=4)
            app.save_project(AEDT)
            app.odesign.GetModule("Solutions").ExportEigenmodes(
                SETUP + " : LastAdaptive", "", path)
        freqs = parse_eig(open(path, encoding="utf-8-sig",
                               errors="ignore").read())
        f1 = freqs[0] if freqs else None
        err = 100 * (f1 - F0_GHZ) / F0_GHZ if f1 else None
        log("tk=%.1f predicted amp=%.3f solved %.1fs f1=%s err=%s%%" %
            (tk, amp, time.time() - t0, f1, err))
        rows.append([tk, round(amp, 4), round(xs, 3), f1, round(err, 4) if err else ""])

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["theta_k_deg", "amp_pred_deg", "Xeff_ohm",
                    "f_hfss_ideal_GHz", "rel_err_pct"])
        for r in rows:
            w.writerow(r)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=160)
        ax.plot([r[0] for r in rows], [r[3] for r in rows if r[3]],
                "o-", color="#d62728", lw=1.8, ms=6,
                label="ideal tensor sheet HFSS")
        ax.axhline(F0_GHZ, color="#1f77b4", ls="--", lw=1.5,
                   label="target 17 GHz")
        ax.set_xlabel("propagation direction theta_k (deg)")
        ax.set_ylabel("f (GHz)")
        ax.set_title("Fitted tensor -> independent HFSS model")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=9)
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
