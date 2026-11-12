# -*- coding: utf-8 -*-
"""Sliced-patch tensor impedance surface: extract Zxx/Zxy/Zyy from HFSS Eigenmode.

Unit cell: p=3 mm, h=1.57 mm, eps_r=2.2 grounded substrate, square PEC patch
with an optional diagonal slice (width g_s, angle theta_s), PEC lid, four
Lattice Pairs driven by phix = k*cos(theta_k), phiy = k*sin(theta_k).

At each propagation direction theta_k, sweep the phase amplitude k, interpolate
f(k) to 17 GHz, convert to beta, and get X_eff = eta0*sqrt((beta/k0)^2 - 1).
A least-squares fit of X_eff(theta) = Xxx*cos^2 + 2*Xxy*cos*sin + Xyy*sin^2
gives the three tensor components, principal values and principal-axis angle.

Run one geometry per invocation:
  CFG=ts60_gs02 THETA_S=60 GS=0.2 python tensor_patch.py
  CFG=ts00_gs00 THETA_S=0 GS=0 THETA_K=0 AMPS=55,60,... python tensor_patch.py
  RUN_MODE=post python tensor_patch.py      # rebuild tables and plots only
AEDT must run in GUI mode.
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
EIG_DIR = os.path.join(ROOT, "eig")
LOG = os.path.join(ROOT, "run.log")
RAW_CSV = os.path.join(ROOT, "eig_points.csv")
XEFF_CSV = os.path.join(ROOT, "Xeff_by_angle.csv")
FIT_CSV = os.path.join(ROOT, "tensor_fit.csv")
PNG_XEFF = os.path.join(ROOT, "tensor_patch.png")
PNG_ANGLE = os.path.join(ROOT, "principal_angle.png")

C0 = 299792458.0
ETA0 = 376.730313668
F0_GHZ = 17.0
P_MM = 3.0
H_SUB = 1.57
H_AIR = 30.0
EPS_R = 2.2
G_MM = 0.2
N_MODES = 8
SETUP = "Eigen1"

CFG = os.environ.get("CFG", "ts60_gs02")
THETA_S = float(os.environ.get("THETA_S", "60"))
GS = float(os.environ.get("GS", "0.2"))
THETA_K = [float(x) for x in os.environ.get(
    "THETA_K", "0,22.5,45,67.5,90").split(",")]
AMPS = [float(x) for x in os.environ.get(
    "AMPS", "55,60,65,70,75,80,85").split(",")]
AEDT = os.path.join(ROOT, "tensor_patch.aedt")
DESIGN = "patch_%s" % CFG


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def clip_halfplane(poly, normal, center, bound, keep_greater):
    """Sutherland-Hodgman clip of a convex polygon by n.(r-c) >= / <= bound."""
    out = []
    for i in range(len(poly)):
        a = poly[i]
        b = poly[(i + 1) % len(poly)]
        da = normal[0] * (a[0] - center[0]) + normal[1] * (a[1] - center[1]) - bound
        db = normal[0] * (b[0] - center[0]) + normal[1] * (b[1] - center[1]) - bound
        ina = da >= 0 if keep_greater else da <= 0
        inb = db >= 0 if keep_greater else db <= 0
        if ina:
            out.append(a)
        if ina != inb:
            t = da / (da - db)
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return out


def patch_polygons(theta_s_deg, g, gs, p):
    lo, hi = g / 2.0, p - g / 2.0
    square = [(lo, lo), (hi, lo), (hi, hi), (lo, hi)]
    ang = math.radians(theta_s_deg)
    normal = (-math.sin(ang), math.cos(ang))
    center = (p / 2.0, p / 2.0)
    half = gs / 2.0
    return (clip_halfplane(square, normal, center, half, True),
            clip_halfplane(square, normal, center, -half, False))


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
    app["g"] = "%smm" % G_MM
    app["hs"] = "%smm" % H_SUB
    app["H"] = "%smm" % H_AIR
    app["phix"] = "70deg"
    app["phiy"] = "0deg"

    mat = app.materials.add_material("Sub22")
    mat.permittivity = EPS_R
    sub = app.modeler.create_box([0, 0, 0], ["p", "p", "hs"],
                                 name="Substrate", material="Sub22")
    air = app.modeler.create_box([0, 0, "hs"], ["p", "p", "H"],
                                 name="Air", material="vacuum")

    if GS <= 0:
        sheet = app.modeler.create_rectangle(
            2, ["g/2", "g/2", "hs"], ["p-g", "p-g"], name="Patch")
        names = [sheet.name]
    else:
        polys = patch_polygons(THETA_S, G_MM, GS, P_MM)
        names = []
        for i, poly in enumerate(polys):
            if len(poly) < 3:
                raise RuntimeError("patch polygon %d degenerated: %r" % (i, poly))
            pts = [[x, y, H_SUB] for x, y in poly]
            obj = app.modeler.create_polyline(
                pts, cover_surface=True, close_surface=True,
                name="Patch%d" % i)
            names.append(obj.name)
        log("slice polygons: %r" % [len(p) for p in polys])
    app.assign_perfecte_to_sheets(names, name="PatchPEC")

    sf = face_map(sub, 0.0, H_SUB)
    af = face_map(air, H_SUB, H_SUB + H_AIR)
    app.assign_perfect_e(sf["bottom"], name="Ground")
    app.assign_perfect_e(af["top"], name="TopPEC")
    pairs = [(sf["x0"], sf["xp"], "phix", "PairSubX"),
             (af["x0"], af["xp"], "phix", "PairAirX"),
             (sf["y0"], sf["yp"], "phiy", "PairSubY"),
             (af["y0"], af["yp"], "phiy", "PairAirY")]
    for fa, fb, var, name in pairs:
        app.assign_lattice_pair([fa, fb], phase_delay="InputPhaseDelay",
                                phase_delay_param1=var, name=name)

    setup = app.create_setup(SETUP, setup_type="HFSSEigen",
                             MinimumFrequency="10GHz", NumModes=N_MODES,
                             MaxDeltaFreq=1, MaximumPasses=10,
                             MinimumPasses=2, MinimumConvergedPasses=2)
    log("setup=%r" % setup.props)
    log("boundaries=%r" % [b.name for b in app.boundaries])
    log("validate=%r" % app.validate_simple())
    app.save_project(AEDT)


def parse_eig(text):
    freqs, q1 = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tok = line.split()
        if len(tok) < 2:
            continue
        value = None
        try:
            value = float(tok[1])
        except ValueError:
            # HFSS may concatenate the frequency and a tiny imaginary part
            m = re.match(r"^\s*\d+\s+([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", line)
            if m:
                value = float(m.group(1))
        if value is None:
            continue
        freqs.append(round(value, 6))
        if q1 is None:
            try:
                q1 = float(tok[-1])
            except ValueError:
                pass
    return freqs[:N_MODES], q1


def solve(app, tk, amp):
    phix = amp * math.cos(math.radians(tk))
    phiy = amp * math.sin(math.radians(tk))
    app["phix"] = "%.6fdeg" % phix
    app["phiy"] = "%.6fdeg" % phiy
    t0 = time.time()
    app.analyze_setup(SETUP, cores=4)
    app.save_project(AEDT)
    tag = "%s_tk%s_a%s" % (CFG, ("%g" % tk).replace(".", "p"),
                           ("%g" % amp).replace(".", "p"))
    path = os.path.join(EIG_DIR, tag + ".eig")
    app.odesign.GetModule("Solutions").ExportEigenmodes(
        SETUP + " : LastAdaptive", "", path)
    freqs, q1 = parse_eig(open(path, encoding="utf-8-sig",
                               errors="ignore").read())
    log("%s tk=%.1f amp=%.1f solved %.1fs f1=%.4f" %
        (CFG, tk, amp, time.time() - t0, freqs[0] if freqs else -1))
    if not freqs:
        raise RuntimeError("no eigen frequencies for tk=%s amp=%s" % (tk, amp))
    return phix, phiy, freqs, q1


def header():
    return (["cfg", "theta_s_deg", "gs_mm", "theta_k_deg", "amp_deg",
             "phix_deg", "phiy_deg"] +
            ["f%d_GHz" % i for i in range(1, N_MODES + 1)] + ["Q1"])


def main():
    if os.environ.get("RUN_MODE") != "post":
        raise RuntimeError(
            "tensor_patch.py is retained for post-processing the historical "
            "121-point dataset only. Use parametric_scan.py for simulation "
            "(one design, theta_s/gs variables, Optimetrics sweep).")
    os.makedirs(EIG_DIR, exist_ok=True)
    lock = AEDT + ".lock"
    if os.path.exists(lock):
        try:
            os.remove(lock)
            log("removed stale lock: %s" % lock)
        except OSError as exc:
            log("stale lock removal failed: %r" % exc)
    done = set()
    if os.path.exists(RAW_CSV):
        with open(RAW_CSV, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                done.add((r["cfg"], float(r["theta_k_deg"]), float(r["amp_deg"])))
    else:
        with open(RAW_CSV, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(header())
    log("CFG=%s theta_s=%.1f gs=%.3f, resume %d points" %
        (CFG, THETA_S, GS, len(done)))

    fresh = not os.path.exists(AEDT)
    app = Hfss(project=(AEDT if not fresh else "TensorPatch_%s" % CFG),
               design=DESIGN, solution_type="Eigenmode", version="2026.1",
               non_graphical=False, new_desktop=True, close_on_exit=False)
    if "Substrate" in app.modeler.object_names:
        log("existing model detected")
    else:
        build(app)

    for tk in THETA_K:
        for amp in AMPS:
            if (CFG, tk, amp) in done:
                continue
            phix, phiy, freqs, q1 = solve(app, tk, amp)
            row = ([CFG, THETA_S, GS, tk, amp, round(phix, 5), round(phiy, 5)] +
                   freqs + [None] * (N_MODES - len(freqs)) + [q1])
            with open(RAW_CSV, "a", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerow(row)
    log("=== solve done for %s ===" % CFG)
    post()


def interp_amp(pts, f0):
    pts = sorted((f, a) for f, a in pts)
    for i in range(len(pts) - 1):
        f1, a1 = pts[i]
        f2, a2 = pts[i + 1]
        if f1 <= f0 <= f2 and f2 > f1:
            return a1 + (f0 - f1) / (f2 - f1) * (a2 - a1)
    return None


def post():
    if not os.path.exists(RAW_CSV):
        log("no data to post-process")
        return
    with open(RAW_CSV, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    k0 = 2.0 * math.pi * F0_GHZ * 1e9 / C0
    groups = {}
    for r in rows:
        key = (r["cfg"], float(r["theta_s_deg"]), float(r["gs_mm"]),
               float(r["theta_k_deg"]))
        groups.setdefault(key, []).append(r)

    xeff = {}
    for key, grp in groups.items():
        cfg, ts, gs, tk = key
        pts = [(float(r["f1_GHz"]), float(r["amp_deg"]))
               for r in grp if r.get("f1_GHz")]
        amp_star = interp_amp(pts, F0_GHZ)
        if amp_star is None:
            log("no 17 GHz crossing for %s tk=%.1f" % (cfg, tk))
            continue
        beta = math.radians(amp_star) / (P_MM * 1e-3)
        if beta <= k0:
            log("beta<=k0 for %s tk=%.1f" % (cfg, tk))
            continue
        xs = ETA0 * math.sqrt((beta / k0) ** 2 - 1)
        xeff.setdefault((cfg, ts, gs), []).append((tk, amp_star, beta, xs))

    with open(XEFF_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["cfg", "theta_s_deg", "gs_mm", "theta_k_deg",
                    "amp_star_deg", "beta_rad_per_m", "Xeff_ohm"])
        for key in sorted(xeff):
            for tk, amp_star, beta, xs in sorted(xeff[key]):
                w.writerow([key[0], key[1], key[2], tk,
                            round(amp_star, 4), round(beta, 3), round(xs, 3)])

    try:
        import numpy as np
    except Exception as exc:
        log("numpy unavailable for fit: %r" % exc)
        return
    fits = []
    with open(FIT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["cfg", "theta_s_deg", "gs_mm", "Xxx_ohm", "Xxy_ohm",
                    "Xyy_ohm", "X_major_ohm", "X_minor_ohm",
                    "principal_angle_deg", "rms_residual_ohm", "n_dirs"])
        for key in sorted(xeff):
            data = sorted(xeff[key])
            if len(data) < 3:
                continue
            th = np.radians([d[0] for d in data])
            y = np.array([d[3] for d in data])
            m = np.column_stack([np.ones_like(th), np.cos(2 * th), np.sin(2 * th)])
            coef, *_ = np.linalg.lstsq(m, y, rcond=None)
            a, b, c = [float(v) for v in coef]
            rad = math.hypot(b, c)
            x_major, x_minor = a + rad, a - rad
            theta_p = 0.5 * math.degrees(math.atan2(c, b))
            rms = float(np.sqrt(np.mean((m @ coef - y) ** 2)))
            row = [key[0], key[1], key[2], round(a + b, 3), round(c, 3),
                   round(a - b, 3), round(x_major, 3), round(x_minor, 3),
                   round(theta_p, 2), round(rms, 3), len(data)]
            w.writerow(row)
            fits.append(row)
            log("fit %s: Xxx=%.1f Xxy=%.1f Xyy=%.1f major=%.1f minor=%.1f "
                "axis=%.1f deg rms=%.2f" %
                (key[0], a + b, c, a - b, x_major, x_minor, theta_p, rms))
    make_plots(xeff, fits)


def make_plots(xeff, fits):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        log("matplotlib unavailable: %r" % exc)
        return
    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=160)
    for key in sorted(xeff):
        data = sorted(xeff[key])
        ax.plot([d[0] for d in data], [d[3] for d in data], "o-", ms=4,
                lw=1.4, label="%s (ts=%.0f, gs=%.1f)" % key)
    ax.set_xlabel("propagation direction theta_k (deg)")
    ax.set_ylabel("effective surface reactance Xeff (ohm)")
    ax.set_title("Sliced-patch unit cell, 17 GHz")
    ax.grid(alpha=0.3)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(PNG_XEFF)
    plt.close(fig)

    if len(fits) >= 2:
        fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=160)
        xs = [r[1] for r in fits]
        ys = [r[8] for r in fits]
        ax.plot(xs, ys, "o-", color="#d62728", lw=1.8, ms=6,
                label="HFSS principal axis")
        ax.plot([0, 90], [0, 90], "--", color="#1f77b4", lw=1.5,
                label="theta_p = theta_s guide")
        ax.set_xlabel("slice angle theta_s (deg)")
        ax.set_ylabel("principal axis angle theta_p (deg)")
        ax.set_title("Principal axis vs slice angle")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=9)
        fig.tight_layout()
        fig.savefig(PNG_ANGLE)
        plt.close(fig)
    log("plots written")


if __name__ == "__main__":
    try:
        if os.environ.get("RUN_MODE") == "post":
            post()
        else:
            main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
