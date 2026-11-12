# -*- coding: utf-8 -*-
"""Replace the rhombic primitive cell with a hexagonal Wigner-Seitz cell.

Regular hexagon, inradius a/2 = 1.5 mm for a = 3 mm (larger than the rhombus
inradius 1.299 mm, so a bigger disc is possible). Three pairs of opposite
sides carry Primary/Secondary boundaries with phases
  phi_v = k.a1, phi_u = k.a2, phi_w = k.(a2-a1) = phi2 - phi1.
Each pair is assigned once for the substrate side and once for the air side.

Run:
  RUN_MODE=probe python hexagonal_ws.py
  RUN_MODE=symmetry python hexagonal_ws.py
  RUN_MODE=tensor python hexagonal_ws.py
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
EIG_DIR = os.path.join(ROOT, "eig_hexagonal_ws")
LOG = os.path.join(ROOT, "hexagonal_ws.log")

DESIGN = "hexagonal"
SETUP = "Eigen1_WS"
N_MODES = 8
A_MM = 3.0
R_HEX = A_MM / math.sqrt(3.0)
R_DISC = 1.35
H_SUB = 1.57
H_AIR = 30.0


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def vertices(z):
    return [[R_HEX * math.cos(math.radians(30 + 60 * k)),
             R_HEX * math.sin(math.radians(30 + 60 * k)), z]
            for k in range(6)]


def as_object(result, fallback, app):
    if isinstance(result, list):
        return result[0] if result else app.modeler[fallback]
    if hasattr(result, "name"):
        return result
    return app.modeler[fallback]


def side_faces(obj, z_mid, tol=0.06):
    """Edge midpoints of the regular hexagon (E0..E5, counter-clockwise)."""
    v = vertices(0)
    mid = {}
    for k in range(6):
        a, b = v[k], v[(k + 1) % 6]
        mid["E%d" % k] = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    out = {}
    for face in obj.faces:
        cx, cy, cz = [float(x) for x in face.center]
        if abs(cz - z_mid) > 0.2:
            continue
        for key, (mx, my) in mid.items():
            if abs(cx - mx) < tol and abs(cy - my) < tol:
                out[key] = face.id
                break
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


def ensure_setup(app):
    if SETUP not in app.setup_names:
        app.create_setup(SETUP, setup_type="HFSSEigen",
                         MinimumFrequency="5GHz", NumModes=N_MODES,
                         MaxDeltaFreq=1, MaximumPasses=10,
                         MinimumPasses=2, MinimumConvergedPasses=2)
        log("created setup %s" % SETUP)


def clear_design(app):
    mod = app.odesign.GetModule("BoundarySetup")
    names = [b.name for b in app.boundaries]
    for n in names:
        try:
            mod.DeleteBoundary(n)
        except Exception as exc:
            log("delete boundary %s failed: %r" % (n, exc))
    objs = list(app.modeler.object_names)
    if objs:
        app.modeler.delete(objs)
    log("cleared %d boundaries, %d objects" % (len(names), len(objs)))


def build(app):
    app.modeler.model_units = "mm"
    for name, value in (("a", "%smm" % A_MM), ("disc_r", "%smm" % R_DISC),
                        ("hs", "%smm" % H_SUB), ("H", "%smm" % H_AIR),
                        ("phi1", "0deg"), ("phi2", "0deg"),
                        ("phi_w", "phi2 - phi1")):
        app[name] = value
    mat = app.materials.add_material("Sub22")
    mat.permittivity = 2.2

    s0 = app.modeler.create_polyline(vertices(0), cover_surface=True,
                                     close_surface=True, name="SubSheet")
    sub = as_object(app.modeler.sweep_along_vector(s0.name, [0, 0, H_SUB]),
                    "SubSheet", app)
    sub.material_name = "Sub22"
    sub.name = "Substrate"
    a0 = app.modeler.create_polyline(vertices(H_SUB), cover_surface=True,
                                     close_surface=True, name="AirSheet")
    air = as_object(app.modeler.sweep_along_vector(a0.name, [0, 0, H_AIR]),
                    "AirSheet", app)
    air.material_name = "vacuum"
    air.name = "Air"
    app.modeler.create_circle(2, ["0mm", "0mm", "%gmm" % H_SUB],
                              "disc_r", name="Disc")
    app.assign_perfecte_to_sheets("Disc", name="PatchPEC")

    cs = cap_faces(sub, 0.0, H_SUB)
    ca = cap_faces(air, H_SUB, H_SUB + H_AIR)
    app.assign_perfect_e(cs["bottom"], name="Ground")
    app.assign_perfect_e(ca["top"], name="TopPEC")

    v = vertices(0)
    # U vectors: same direction on each opposite pair.
    pairs = (
        # (primary edge, secondary edge, primary U start/end, secondary U start/end, phase)
        ("E5", "E2", v[5], v[0], v[3], v[2], "phi1"),
        ("E0", "E3", v[0], v[1], v[4], v[3], "phi2"),
        ("E1", "E4", v[1], v[2], v[5], v[4], "phi_w"),
    )
    for layer, obj, z in (("Sub", sub, H_SUB / 2),
                          ("Air", air, H_SUB + H_AIR / 2)):
        faces = side_faces(obj, z)
        log("%s side faces=%r" % (layer, faces))
        if len(faces) < 6:
            raise RuntimeError("hexagon side face detection incomplete")
        for ep, es, up0, up1, us0, us1, phase in pairs:
            p = app.assign_primary(
                faces[ep], [up0[0], up0[1], z], [up1[0], up1[1], z],
                name="P_%s_%s" % (layer, ep))
            app.assign_secondary(
                faces[es], p.name,
                [us0[0], us0[1], z], [us1[0], us1[1], z],
                phase_delay="InputPhaseDelay", phase_delay_param1=phase,
                name="S_%s_%s" % (layer, es))

    ensure_setup(app)
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


def eigen(app, tag):
    path = os.path.join(EIG_DIR, tag + ".eig")
    app.odesign.GetModule("Solutions").ExportEigenmodes(
        SETUP + " : LastAdaptive", "", path)
    return parse_eig(open(path, encoding="utf-8-sig",
                          errors="ignore").read())


def solve(app, p1, p2, tag):
    app["phi1"] = "%gdeg" % p1
    app["phi2"] = "%gdeg" % p2
    t0 = time.time()
    app.analyze_setup(SETUP, cores=4)
    f = eigen(app, tag)
    log("phi1=%g phi2=%g solved %.1fs modes=%r" %
        (p1, p2, time.time() - t0, f[:5]))
    return f


def run_symmetry(app):
    cases = ((90, 0), (0, 90), (60, 0), (0, 60))
    out = {}
    for p1, p2 in cases:
        out[(p1, p2)] = solve(app, p1, p2, "sym_%d_%d" % (p1, p2))
    with open(os.path.join(ROOT, "hexagonal_ws_symmetry.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["phi1_deg", "phi2_deg", "f1_GHz", "f2_GHz", "f3_GHz"])
        for k, f in out.items():
            w.writerow([k[0], k[1]] + (f[:3] + [None] * (3 - len(f[:3]))))
    for phi in (90, 60):
        a, b = out[(phi, 0)], out[(0, phi)]
        if a and b:
            log("symmetry phi=%g f1 %.4f vs %.4f diff %.4f GHz" %
                (phi, a[0], b[0], abs(a[0] - b[0])))


def interp_amp(pts, f0):
    pts = sorted((f, a) for f, a in pts)
    for i in range(len(pts) - 1):
        f1, a1 = pts[i]
        f2, a2 = pts[i + 1]
        if f1 <= f0 <= f2 and f2 > f1:
            return a1 + (f0 - f1) / (f2 - f1) * (a2 - a1)
    return None


def run_tensor(app):
    k0 = 2.0 * math.pi * 17.0e9 / 299792458.0
    eta0 = 376.730313668
    rows = []
    for theta in (0, 22.5, 45, 67.5, 90):
        c, s = math.cos(math.radians(theta)), math.sin(math.radians(theta))
        pts = []
        for amp in (50, 60, 70, 80):
            f = solve(app, amp * c, amp * (0.5 * c + math.sqrt(3) / 2 * s),
                      "t%g_a%d" % (theta, amp))
            if f:
                pts.append((f[0], amp))
        amp_star = interp_amp(pts, 17.0)
        if amp_star is None:
            log("theta=%.1f no 17GHz crossing" % theta)
            continue
        beta = math.radians(amp_star) / (A_MM * 1e-3)
        ratio = beta / k0
        xs = eta0 * math.sqrt(ratio ** 2 - 1) if ratio > 1 else None
        rows.append([theta, round(amp_star, 3), round(beta, 2),
                     round(ratio, 4), round(xs, 2) if xs else ""])
        log("theta=%.1f amp*=%.3f beta/k0=%.4f Xeff=%s" %
            (theta, amp_star, ratio, "%.2f" % xs if xs else "n/a"))
    with open(os.path.join(ROOT, "hexagonal_ws_inverse.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["theta_deg", "amp_star_deg", "beta_rad_per_m",
                    "beta_over_k0", "Xeff_ohm"])
        for r in rows:
            w.writerow(r)


def main():
    mode = os.environ.get("RUN_MODE", "probe")
    os.makedirs(EIG_DIR, exist_ok=True)
    lock = AEDT + ".lock"
    if os.path.exists(lock):
        os.remove(lock)
    app = Hfss(project=AEDT, design=DESIGN, solution_type="Eigenmode",
               version="2026.1", non_graphical=False, new_desktop=True,
               close_on_exit=False)
    # A hexagonal WS cell has 6 side faces; the old rhombus has 4.
    sub = app.modeler["Substrate"] if "Substrate" in app.modeler.object_names else None
    need_build = sub is None or len(side_faces(sub, H_SUB / 2)) != 6
    if need_build:
        if sub is not None:
            clear_design(app)
        build(app)
    else:
        log("existing hexagonal WS cell detected")
    ensure_setup(app)

    if mode == "symmetry":
        run_symmetry(app)
    elif mode == "tensor":
        run_tensor(app)
    else:
        solve(app, 0, 0, "probe")
    app.save_project(AEDT)
    log("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
