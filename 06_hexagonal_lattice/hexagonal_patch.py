# -*- coding: utf-8 -*-
"""Hexagonal (triangular) lattice of circular patches: rhombic primitive cell.

Cell vectors a1 = a*(1,0), a2 = a*(1/2, sqrt(3)/2). A rhombic prism is swept
from a 2D polyline; two pairs of Primary/Secondary boundaries carry phases
phi1 = k.a1 and phi2 = k.a2, with explicit U vectors for the oblique faces.
"""
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
LOG = os.path.join(ROOT, "hexagonal.log")
EIG_DIR = os.path.join(ROOT, "eig_hexagonal")

DESIGN = "hexagonal"
SETUP = "Eigen1_Low"
N_MODES = 8
A_MM = 3.0
R_MM = 1.117
H_SUB = 1.57
H_AIR = 30.0
SQ3 = math.sqrt(3.0)


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def rhombus(z):
    return [[0, 0, z], [A_MM, 0, z],
            [1.5 * A_MM, SQ3 / 2 * A_MM, z],
            [0.5 * A_MM, SQ3 / 2 * A_MM, z]]


def side_faces(obj, z_mid, tol=1e-4):
    """Map rhombus side faces by their centre coordinates."""
    out = {}
    for face in obj.faces:
        cx, cy, cz = [float(v) for v in face.center]
        if abs(cz - z_mid) > 0.2:
            continue
        if abs(cy) < tol:
            out["OA"] = face.id
        elif abs(cy - SQ3 / 2 * A_MM) < tol:
            out["CB"] = face.id
        elif abs(cx - 0.25 * A_MM) < tol:
            out["OC"] = face.id
        elif abs(cx - 1.25 * A_MM) < tol:
            out["AB"] = face.id
    return out


def cap_faces(obj, z_lo, z_hi, tol=1e-4):
    out = {}
    for face in obj.faces:
        cz = float(face.center[2])
        if abs(cz - z_lo) < tol:
            out["bottom"] = face.id
        elif abs(cz - z_hi) < tol:
            out["top"] = face.id
    return out


def as_object(result, fallback_name, app):
    if isinstance(result, list):
        return result[0] if result else app.modeler[fallback_name]
    if hasattr(result, "name"):
        return result
    return app.modeler[fallback_name]


def build(app):
    app.modeler.model_units = "mm"
    for name, value in (("a", "%smm" % A_MM), ("disc_r", "%smm" % R_MM),
                        ("hs", "%smm" % H_SUB), ("H", "%smm" % H_AIR),
                        ("phi1", "0deg"), ("phi2", "0deg")):
        app[name] = value
    mat = app.materials.add_material("Sub22")
    mat.permittivity = 2.2

    s0 = app.modeler.create_polyline(rhombus(0), cover_surface=True,
                                     close_surface=True, name="SubSheet")
    sub = as_object(app.modeler.sweep_along_vector(s0.name, [0, 0, H_SUB]),
                    "SubSheet", app)
    sub.material_name = "Sub22"
    sub.name = "Substrate"

    a0 = app.modeler.create_polyline(rhombus(H_SUB), cover_surface=True,
                                     close_surface=True, name="AirSheet")
    air = as_object(app.modeler.sweep_along_vector(a0.name, [0, 0, H_AIR]),
                    "AirSheet", app)
    air.material_name = "vacuum"
    air.name = "Air"

    cx, cy = 0.75 * A_MM, SQ3 / 4 * A_MM
    app.modeler.create_circle(
        2, ["%gmm" % cx, "%gmm" % cy, "%gmm" % H_SUB], "disc_r", name="Disc")
    app.assign_perfecte_to_sheets("Disc", name="PatchPEC")

    caps_s = cap_faces(sub, 0.0, H_SUB)
    caps_a = cap_faces(air, H_SUB, H_SUB + H_AIR)
    app.assign_perfect_e(caps_s["bottom"], name="Ground")
    app.assign_perfect_e(caps_a["top"], name="TopPEC")

    sf = side_faces(sub, H_SUB / 2)
    af = side_faces(air, H_SUB + H_AIR / 2)
    log("substrate side faces=%r" % sf)
    log("air side faces=%r" % af)
    if len(sf) < 4 or len(af) < 4:
        raise RuntimeError("rhombus side face detection incomplete")

    z_s, z_a = H_SUB / 2, H_SUB + H_AIR / 2
    for layer, faces, z in (("Sub", sf, z_s), ("Air", af, z_a)):
        # Pair 1: OA <-> CB translated by a2; phase phi2
        p = app.assign_primary(
            faces["OA"], [0, 0, z], [A_MM, 0, z],
            name="P_%s_OA" % layer)
        app.assign_secondary(
            faces["CB"], p.name,
            [0.5 * A_MM, SQ3 / 2 * A_MM, z],
            [1.5 * A_MM, SQ3 / 2 * A_MM, z],
            phase_delay="InputPhaseDelay", phase_delay_param1="phi2",
            name="S_%s_CB" % layer)
        # Pair 2: OC <-> AB translated by a1; phase phi1
        p = app.assign_primary(
            faces["OC"], [0, 0, z], [0.5 * A_MM, SQ3 / 2 * A_MM, z],
            name="P_%s_OC" % layer)
        app.assign_secondary(
            faces["AB"], p.name,
            [A_MM, 0, z], [1.5 * A_MM, SQ3 / 2 * A_MM, z],
            phase_delay="InputPhaseDelay", phase_delay_param1="phi1",
            name="S_%s_AB" % layer)

    app.create_setup(SETUP, setup_type="HFSSEigen",
                     MinimumFrequency="5GHz", NumModes=N_MODES,
                     MaxDeltaFreq=1, MaximumPasses=10,
                     MinimumPasses=2, MinimumConvergedPasses=2)
    log("objects=%r" % app.modeler.object_names)
    log("boundaries=%r" % [b.name for b in app.boundaries])
    log("validate=%r" % app.validate_simple())
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
    sol.ExportEigenmodes(SETUP + " : LastAdaptive", "", path)
    return parse_eig(open(path, encoding="utf-8-sig",
                          errors="ignore").read())


def interp_amp(pts, f0):
    pts = sorted((f, a) for f, a in pts)
    for i in range(len(pts) - 1):
        f1, a1 = pts[i]
        f2, a2 = pts[i + 1]
        if f1 <= f0 <= f2 and f2 > f1:
            return a1 + (f0 - f1) / (f2 - f1) * (a2 - a1)
    return None


def run_tensor(app):
    import csv
    import numpy as np
    k0 = 2.0 * math.pi * 17.0e9 / 299792458.0
    eta0 = 376.730313668
    rows = []
    for theta in (0, 22.5, 45, 67.5, 90):
        c, s = math.cos(math.radians(theta)), math.sin(math.radians(theta))
        by_amp = {}
        for amp in (60, 70, 80):
            app["phi1"] = "%.6fdeg" % (amp * c)
            app["phi2"] = "%.6fdeg" % (amp * (0.5 * c + SQ3 / 2 * s))
            t0 = time.time()
            app.analyze_setup(SETUP, cores=4)
            freqs = eigen_freqs(app, "t%g_a%d" % (theta, amp))
            by_amp[amp] = freqs
            log("theta=%.1f amp=%d solved %.1fs modes=%r" %
                (theta, amp, time.time() - t0, freqs[:6]))
        # Track one branch by frequency continuity instead of taking mode 1.
        mid = by_amp.get(70, [])
        if not mid:
            continue
        k = min(range(len(mid)), key=lambda i: abs(mid[i] - 17.0))
        f70 = mid[k]
        f60 = min(by_amp.get(60, []), key=lambda f: abs(f - f70), default=None)
        f80 = min(by_amp.get(80, []), key=lambda f: abs(f - f70), default=None)
        log("theta=%.1f tracked f60/f70/f80=%s/%.4f/%s (mode %d at 70)" %
            (theta, f60, f70, f80, k + 1))
        pts = []
        if f60 is not None:
            pts.append((f60, 60))
        pts.append((f70, 70))
        if f80 is not None:
            pts.append((f80, 80))
        amp_star = interp_amp(pts, 17.0)
        if amp_star is None:
            log("no 17GHz crossing at theta=%.1f" % theta)
            continue
        beta = math.radians(amp_star) / (A_MM * 1e-3)
        if beta <= k0:
            log("theta=%.1f beta=%.1f <= k0=%.1f, no bound surface wave" %
                (theta, beta, k0))
            continue
        xs = eta0 * math.sqrt((beta / k0) ** 2 - 1)
        rows.append((theta, amp_star, beta, xs))
        log("theta=%.1f amp*=%.3f Xeff=%.2f" % (theta, amp_star, xs))
    with open(os.path.join(ROOT, "hexagonal_xeff.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["theta_deg", "amp_star_deg", "beta_rad_per_m", "Xeff_ohm"])
        for r in rows:
            w.writerow([r[0], round(r[1], 4), round(r[2], 3), round(r[3], 3)])
    if len(rows) >= 3:
        th = np.radians([r[0] for r in rows])
        y = np.array([r[3] for r in rows])
        m = np.column_stack([np.ones_like(th), np.cos(2 * th), np.sin(2 * th)])
        coef, *_ = np.linalg.lstsq(m, y, rcond=None)
        a, b, c2 = [float(v) for v in coef]
        rms = float(np.sqrt(np.mean((m @ coef - y) ** 2)))
        log("fit Xxx=%.2f Xxy=%.2f Xyy=%.2f axis=%.2f rms=%.2f" %
            (a + b, c2, a - b, 0.5 * math.degrees(math.atan2(c2, b)), rms))
        with open(os.path.join(ROOT, "hexagonal_fit.csv"), "w",
                  newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Xxx_ohm", "Xxy_ohm", "Xyy_ohm",
                        "principal_axis_deg", "rms_ohm", "n_dirs"])
            w.writerow([round(a + b, 3), round(c2, 3), round(a - b, 3),
                        round(0.5 * math.degrees(math.atan2(c2, b)), 2),
                        round(rms, 3), len(rows)])
    app.save_project(AEDT)


def run_dispersion(app):
    import csv
    rows = []
    for phi1 in (0, 30, 60, 90, 120, 150, 180):
        app["phi1"] = "%ddeg" % phi1
        app["phi2"] = "0deg"
        t0 = time.time()
        app.analyze_setup(SETUP, cores=4)
        freqs = eigen_freqs(app, "gm%d" % phi1)
        beta = math.radians(phi1) / (A_MM * 1e-3)
        f_light = 299792458.0 * beta / (2 * math.pi) / 1e9
        rows.append([phi1, beta, f_light] + freqs[:3] +
                    [None] * (3 - len(freqs[:3])))
        log("Gamma-M phi1=%d solved %.1fs f1=%.4f light=%.3f" %
            (phi1, time.time() - t0, freqs[0] if freqs else -1, f_light))
    with open(os.path.join(ROOT, "hexagonal_dispersion.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["phi1_deg", "beta_rad_per_m", "light_line_GHz",
                    "f1_GHz", "f2_GHz", "f3_GHz"])
        for r in rows:
            w.writerow(r)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=160)
        xs = [r[0] for r in rows]
        for idx, label in ((3, "mode 1"), (4, "mode 2"), (5, "mode 3")):
            ys = [r[idx] for r in rows if r[idx] is not None]
            if ys:
                ax.plot(xs[:len(ys)], ys, "o-", ms=4, lw=1.4, label=label)
        ax.plot(xs, [r[2] for r in rows], "--", color="#888780", lw=1.5,
                label="light line")
        ax.set_xlabel("phase phi1 along a1 (deg)")
        ax.set_ylabel("f (GHz)")
        ax.set_title("Hexagonal lattice, Gamma to M")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=9)
        fig.tight_layout()
        fig.savefig(os.path.join(ROOT, "hexagonal_dispersion.png"))
        plt.close(fig)
        log("dispersion plot written")
    except Exception as exc:
        log("plot failed: %r" % exc)
    app.save_project(AEDT)


def main():
    mode = os.environ.get("RUN_MODE", "probe")
    os.makedirs(EIG_DIR, exist_ok=True)
    lock = AEDT + ".lock"
    if os.path.exists(lock):
        os.remove(lock)
    app = Hfss(project=AEDT, design=DESIGN, solution_type="Eigenmode",
               version="2026.1", non_graphical=False, new_desktop=True,
               close_on_exit=False)
    if "Disc" not in app.modeler.object_names:
        build(app)
    else:
        log("existing hexagonal design detected")
    if mode == "tensor":
        app["disc_r"] = "1.28mm"
        log("disc_r set to 1.28mm (rhombus inradius 1.299mm)")
        run_tensor(app)
    elif mode == "dispersion":
        app["disc_r"] = "1.28mm"
        run_dispersion(app)
    else:
        app["phi1"] = "0deg"
        app["phi2"] = "0deg"
        t0 = time.time()
        app.analyze_setup(SETUP, cores=4)
        app.save_project(AEDT)
        freqs = eigen_freqs(app, "probe")
        log("probe solved %.1fs freqs=%r" % (time.time() - t0, freqs))
    log("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
