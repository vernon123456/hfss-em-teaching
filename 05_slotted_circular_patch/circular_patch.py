# -*- coding: utf-8 -*-
"""Slotted circular patch unit cell: geometry-to-tensor mapping.

Unit cell: p=3 mm, substrate 1.57 mm eps_r=2.2, PEC ground and lid.
A circular PEC disc of radius patch_r carries one rectangular slot of width
slot_w, rotated by slot_ang about a relative CS at the cell centre.
All four quantities are AEDT design variables, so Optimetrics can sweep them
and Python loops can drive the propagation direction via phix/phiy.

Run:
  RUN_MODE=probe python circular_patch.py    # build + one point
  RUN_MODE=tensor python circular_patch.py   # script sweep -> Xeff, tensor fit
  RUN_MODE=sweep  python circular_patch.py   # Optimetrics geometry sweep
  RUN_MODE=post   python circular_patch.py   # tables and plots only
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
EIG_DIR = os.path.join(ROOT, "eig_circular")
LOG = os.path.join(ROOT, "circular.log")
TENSOR_CSV = os.path.join(ROOT, "circular_xeff.csv")
FIT_CSV = os.path.join(ROOT, "circular_fit.csv")
SWEEP_CSV = os.path.join(ROOT, "circular_sweep.csv")
XEFF_PNG = os.path.join(ROOT, "circular_xeff.png")
AXIS_PNG = os.path.join(ROOT, "circular_axis.png")

DESIGN = "circular"
SETUP = "Eigen1"
PARAM_SETUP = "SweepCircular"
P_MM = 3.0
H_SUB = 1.57
H_AIR = 30.0
F0_GHZ = 17.0
C0 = 299792458.0
ETA0 = 376.730313668
N_MODES = 12
SLOT_ANGS = (0, 45, 90)
SLOT_W_MAIN = 0.4
SLOT_W_DEGEN = 0.1
THETA_KS = (0, 22.5, 45, 67.5, 90)
AMPS = (60, 70, 80)


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
    for name, value in (("p", "%smm" % P_MM), ("hs", "%smm" % H_SUB),
                        ("H", "%smm" % H_AIR), ("patch_r", "1.2mm"),
                        ("slot_w", "%smm" % SLOT_W_MAIN),
                        ("slot_ang", "45deg"), ("phix", "70deg"),
                        ("phiy", "0deg")):
        app[name] = value
    mat = app.materials.add_material("Sub22")
    mat.permittivity = 2.2
    sub = app.modeler.create_box([0, 0, 0], ["p", "p", "hs"],
                                 name="Substrate", material="Sub22")
    air = app.modeler.create_box([0, 0, "hs"], ["p", "p", "H"],
                                 name="Air", material="vacuum")
    app.modeler.create_circle(2, ["p/2", "p/2", "hs"], "patch_r",
                              name="Disc")
    app.modeler.create_rectangle(2, ["p/2 - p", "p/2 - slot_w/2", "hs"],
                                 ["2*p", "slot_w"], name="Slot")
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
         "RotateAngle:=", "slot_ang", "CoordinateSystem:=", "CS_center"])
    if not app.modeler.subtract("Disc", "Slot", keep_originals=False):
        raise RuntimeError("slot subtraction failed")
    app.assign_perfecte_to_sheets("Disc", name="PatchPEC")

    sf = face_map(sub, 0.0, H_SUB, P_MM)
    af = face_map(air, H_SUB, H_SUB + H_AIR, P_MM)
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


def eigen_freqs(app, tag):
    sol = app.odesign.GetModule("Solutions")
    path = os.path.join(EIG_DIR, tag + ".eig")
    # Empty key exports the current nominal solution. ListVariations accumulates
    # every solved variation, so keys[0] would return a stale cached result.
    sol.ExportEigenmodes(SETUP + " : LastAdaptive", "", path)
    return parse_eig(open(path, encoding="utf-8-sig",
                          errors="ignore").read())


def solve(app, tag):
    t0 = time.time()
    app.analyze_setup(SETUP, cores=4)
    freqs = eigen_freqs(app, tag)
    log("%s solved %.1fs f1=%.4f" %
        (tag, time.time() - t0, freqs[0] if freqs else -1))
    if not freqs:
        raise RuntimeError("no eigen frequencies for %s" % tag)
    return freqs


def interp_amp(pts, f0):
    pts = sorted((f, a) for f, a in pts)
    for i in range(len(pts) - 1):
        f1, a1 = pts[i]
        f2, a2 = pts[i + 1]
        if f1 <= f0 <= f2 and f2 > f1:
            return a1 + (f0 - f1) / (f2 - f1) * (a2 - a1)
    return None


def run_tensor(app):
    k0 = 2.0 * math.pi * F0_GHZ * 1e9 / C0
    rows = []
    cases = [(sa, SLOT_W_MAIN) for sa in SLOT_ANGS]
    cases.append((0, SLOT_W_DEGEN))
    for sa, sw in cases:
        app["slot_ang"] = "%ddeg" % sa
        app["slot_w"] = "%gmm" % sw
        pts_by_tk = {}
        for tk in THETA_KS:
            pts = []
            for amp in AMPS:
                app["phix"] = "%.6fdeg" % (amp * math.cos(math.radians(tk)))
                app["phiy"] = "%.6fdeg" % (amp * math.sin(math.radians(tk)))
                tag = "sa%d_w%g_tk%g_a%d" % (sa, sw * 10, tk, amp)
                freqs = solve(app, tag)
                pts.append((freqs[0], amp))
            pts_by_tk[tk] = pts
        for tk, pts in pts_by_tk.items():
            amp_star = interp_amp(pts, F0_GHZ)
            if amp_star is None:
                log("no 17GHz crossing sa=%d w=%.2f tk=%.1f" % (sa, sw, tk))
                continue
            beta = math.radians(amp_star) / (P_MM * 1e-3)
            if beta <= k0:
                continue
            xs = ETA0 * math.sqrt((beta / k0) ** 2 - 1)
            rows.append((sa, sw, tk, amp_star, beta, xs))
            log("sa=%d w=%.2f tk=%.1f amp*=%.3f Xeff=%.2f" %
                (sa, sw, tk, amp_star, xs))
    with open(TENSOR_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["slot_ang_deg", "slot_w_mm", "theta_k_deg",
                    "amp_star_deg", "beta_rad_per_m", "Xeff_ohm"])
        for r in rows:
            w.writerow([r[0], r[1], r[2], round(r[3], 4),
                        round(r[4], 3), round(r[5], 3)])
    fit_tensors(rows)


def fit_tensors(rows):
    try:
        import numpy as np
    except Exception as exc:
        log("numpy unavailable: %r" % exc)
        return
    groups = {}
    for sa, sw, tk, amp_star, beta, xs in rows:
        groups.setdefault((sa, sw), []).append((tk, xs))
    fits = []
    with open(FIT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["slot_ang_deg", "slot_w_mm", "Xxx_ohm", "Xxy_ohm",
                    "Xyy_ohm", "X_major_ohm", "X_minor_ohm",
                    "principal_axis_deg", "rms_residual_ohm", "n_dirs"])
        for key in sorted(groups):
            data = sorted(groups[key])
            if len(data) < 3:
                continue
            th = np.radians([d[0] for d in data])
            y = np.array([d[1] for d in data])
            m = np.column_stack([np.ones_like(th), np.cos(2 * th), np.sin(2 * th)])
            coef, *_ = np.linalg.lstsq(m, y, rcond=None)
            a, b, c = [float(v) for v in coef]
            rad = math.hypot(b, c)
            axis = 0.5 * math.degrees(math.atan2(c, b))
            rms = float(np.sqrt(np.mean((m @ coef - y) ** 2)))
            row = [key[0], key[1], round(a + b, 3), round(c, 3),
                   round(a - b, 3), round(a + rad, 3), round(a - rad, 3),
                   round(axis, 2), round(rms, 3), len(data)]
            w.writerow(row)
            fits.append(row)
            log("fit sa=%d w=%.2f Xxx=%.1f Xxy=%.1f Xyy=%.1f axis=%.1f rms=%.2f" %
                (key[0], key[1], a + b, c, a - b, axis, rms))
    make_plots(groups, fits)


def make_plots(groups, fits):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        log("matplotlib unavailable: %r" % exc)
        return
    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=160)
    for key in sorted(groups):
        data = sorted(groups[key])
        ax.plot([d[0] for d in data], [d[1] for d in data], "o-", ms=4,
                lw=1.4, label="slot_ang=%d w=%.2f" % key)
    ax.set_xlabel("propagation direction theta_k (deg)")
    ax.set_ylabel("effective surface reactance Xeff (ohm)")
    ax.set_title("Slotted circular patch, 17 GHz")
    ax.grid(alpha=0.3)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(XEFF_PNG)
    plt.close(fig)
    strong = [r for r in fits if abs(r[1] - SLOT_W_MAIN) < 1e-6]
    if len(strong) >= 2:
        fig, ax = plt.subplots(figsize=(7.0, 4.2), dpi=160)
        ax.plot([r[0] for r in strong], [r[7] for r in strong],
                "o-", color="#d62728", lw=1.8, ms=6,
                label="slotted circular patch")
        ax.plot([0, 90], [0, 90], "--", color="#1f77b4", lw=1.4,
                label="axis = slot_ang guide")
        ax.set_xlabel("slot angle (deg)")
        ax.set_ylabel("principal axis angle (deg)")
        ax.set_title("Principal axis vs slot angle")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=9)
        fig.tight_layout()
        fig.savefig(AXIS_PNG)
        plt.close(fig)
    log("plots written")


def run_sweep(app):
    app["phix"] = "70deg"
    app["phiy"] = "0deg"
    if PARAM_SETUP in [s.name for s in app.parametrics.setups]:
        app.parametrics.delete(PARAM_SETUP)
    setup = app.parametrics.add(
        "slot_ang", 0, 90, 30, variation_type="LinearStep",
        solution=SETUP + " : LastAdaptive", name=PARAM_SETUP)
    setup.add_variation("slot_w", 0.1, 0.5, 0.2, units="mm",
                        variation_type="LinearStep")
    log("sweep props=%r" % setup.props["Sweeps"])
    sol = app.odesign.GetModule("Solutions")
    before_keys = set(sol.ListVariations(SETUP + " : LastAdaptive"))
    t0 = time.time()
    setup.analyze()
    log("sweep solved in %.1fs" % (time.time() - t0))
    app.save_project(AEDT)
    keys = [k for k in sol.ListVariations(SETUP + " : LastAdaptive")
            if k not in before_keys]
    log("sweep variations: %d" % len(keys))
    rows = []
    for idx, key in enumerate(keys):
        path = os.path.join(EIG_DIR, "sweep%02d.eig" % idx)
        try:
            sol.ExportEigenmodes(SETUP + " : LastAdaptive", key, path)
            freqs = parse_eig(open(path, encoding="utf-8-sig",
                                   errors="ignore").read())
        except Exception as exc:
            log("sweep export %s failed: %r" % (key, exc))
            freqs = []
        ma = re.search(r"slot_ang='([^']+)'", key)
        mw = re.search(r"slot_w='([^']+)'", key)
        rows.append([key, ma.group(1) if ma else "",
                     mw.group(1) if mw else ""] + freqs +
                    [None] * (N_MODES - len(freqs)))
        log("sweep var%02d f1=%s" % (idx, freqs[0] if freqs else "n/a"))
    with open(SWEEP_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["variation", "slot_ang", "slot_w"] +
                   ["f%d_GHz" % i for i in range(1, N_MODES + 1)])
        for r in rows:
            w.writerow(r)


def main():
    mode = os.environ.get("RUN_MODE", "probe")
    if mode == "post":
        rows = []
        with open(TENSOR_CSV, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                rows.append((float(r["slot_ang_deg"]), float(r["slot_w_mm"]),
                             float(r["theta_k_deg"]), float(r["amp_star_deg"]),
                             float(r["beta_rad_per_m"]), float(r["Xeff_ohm"])))
        fit_tensors(rows)
        return
    os.makedirs(EIG_DIR, exist_ok=True)
    lock = AEDT + ".lock"
    if os.path.exists(lock):
        os.remove(lock)
        log("removed stale lock")
    app = Hfss(project=AEDT, design=DESIGN, solution_type="Eigenmode",
               version="2026.1", non_graphical=False, new_desktop=True,
               close_on_exit=False)
    if "Disc" not in app.modeler.object_names:
        build(app)
    else:
        log("existing circular design detected")

    if mode == "probe":
        app["slot_ang"] = "45deg"
        app["slot_w"] = "%gmm" % SLOT_W_MAIN
        app["phix"] = "70deg"
        app["phiy"] = "0deg"
        solve(app, "probe")
    elif mode == "tensor":
        run_tensor(app)
        app.save_project(AEDT)
    elif mode == "sweep":
        run_sweep(app)
    else:
        raise RuntimeError("unknown RUN_MODE %r" % mode)
    log("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
