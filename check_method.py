"""Check the water-mapping method on simulated radar scenes where the true water area is known.

    pip install numpy scipy h5py pyproj pillow matplotlib nbformat
    python check_method.py

The script builds 11 fake NISAR GCOV files with the same layout as the real ones. They copy what we saw in the
real Toktogul scenes: a dry plain as dark as the water, two dates with wet (bright) ground, radar stripes, a windy
date, a bay behind a narrow neck and an eastern arm that fills up. Then it runs the code cells of
toktogul_nisar_v2.ipynb on these files (login and download are skipped) and compares the measured area with the truth.

AI disclosure: written with the help of an AI assistant (Claude by Anthropic).
"""
import glob
import json
import os
import shutil
import sys

import matplotlib
matplotlib.use("Agg")
import h5py
import nbformat
import numpy as np
from pyproj import Transformer
from scipy import ndimage as ndi

NOTEBOOK = "toktogul_nisar_v2.ipynb"
WORK = "_check"
DATES = ["20260620", "20260702", "20260714", "20260726", "20260819", "20260831",
         "20260912", "20260924", "20261006", "20261018", "20261030"]
ARM = [4000, 9000, 10500, 11200, 12200, 12500, 12700, 12800, 12800, 12600, 11600]   # length of the flooded eastern arm, m
WET = {7: (4.3, 2.4), 8: (2.3, 1.3)}                                    # date index -> (HH, HV) brightening of wet ground, dB
WIND = [-1.2, 0.3, -0.2, -2.2, 0.8, 0.4, 0.4, 0.2, 1.2, -0.1, -0.9]     # date-to-date change of the water HH, dB


def simulate(ns, folder):
    """Write the fake scenes and return the true water area (km2) for every date."""
    rng = np.random.default_rng(11)
    epsg = 32643
    xmin, xmax, ymin, ymax = ns["aoi_xy"](epsg)
    x = np.arange(np.floor((xmin - 3000) / 20) * 20 + 10, xmax + 3000, 20.0)
    y = np.arange(np.ceil((ymax + 3000) / 20) * 20 - 10, ymin - 3000, -20.0)
    X, Y = np.meshgrid(x, y)
    sx, sy = Transformer.from_crs(4326, epsg, always_xy=True).transform(*ns["SEED"])
    ell = lambda cx, cy, a, b: ((X - cx) / a) ** 2 + ((Y - cy) / b) ** 2 <= 1

    def field(scale_px, amp):
        f = rng.normal(size=(X.shape[0] // 40 + 2, X.shape[1] // 40 + 2))
        f = ndi.zoom(ndi.gaussian_filter(f, scale_px / 40), 40, order=1)[:X.shape[0], :X.shape[1]]
        return amp * f / f.std()

    mount_hh, mount_hv = -9 + field(300, 3.0), -16 + field(300, 2.5)
    plain_hh, plain_hv = -15.2 + field(200, 0.7), -21.7 + field(200, 0.4)
    island = ell(sx - 5000, sy + 800, 600, 600)
    plain = ell(sx + 2000, sy, 22000, 8500)                               # dry plain all around the reservoir
    bay = ell(sx - 8000, sy + 4700, 900, 700)                             # bay behind a 40 m neck
    neck = (np.abs(X - (sx - 8000)) <= 20) & (Y > sy + 3000) & (Y < sy + 4700)
    nodata = ell(sx - 25000, sy - 9000, 900, 500) | ell(sx - 22000, sy - 11000, 500, 900)
    water_of = lambda length: (ell(sx, sy, 14500, 4400) | ell(sx + 12500 + length / 2, sy - 600, length / 2 + 1500, 1300)
                               | ell(sx + 3000, sy + 4200, 1500, 2300) | bay | neck) & ~island
    flood_zone = water_of(max(ARM))
    truth = {}
    for t, (date, length) in enumerate(zip(DATES, ARM)):
        water = water_of(length)
        wet_hh, wet_hv = WET.get(t, (0.0, 0.0))
        hh = np.where(plain, plain_hh + wet_hh, mount_hh + 0.6 * wet_hh)
        hv = np.where(plain, plain_hv + wet_hv, mount_hv + 0.6 * wet_hv)
        bed = flood_zone & ~water                                         # exposed bed of the reservoir: damp sand and silt
        hh = np.where(bed, -13.6 + wet_hh, hh)
        hv = np.where(bed, -20.4 + wet_hv, hv)
        stripes = 0.9 * (np.sin((X + 0.35 * Y) / 1700.0 + t) > 0.75)      # bright stripes on dark water
        water_hh = -17.5 + WIND[t] + stripes
        if t == 4:
            water_hh = water_hh + 3.0 * ell(sx - 1000, sy, 5000, 1800)    # wind patch right over the seed point
        hh = np.where(water, water_hh, hh)
        hv = np.where(water, -23.0 + 0.3 * np.sin(t), hv)
        looks = 6                                                         # radar grain (speckle)
        hh_p = (10 ** (hh / 10) * rng.gamma(looks, 1 / looks, X.shape)).astype("float32")
        hv_p = (10 ** (hv / 10) * rng.gamma(looks, 1 / looks, X.shape)).astype("float32")
        hh_p[nodata] = np.nan
        hv_p[nodata] = np.nan
        name = f"NISAR_L2_PR_GCOV_023_092_D_067_2005_DHDH_A_{date}T140913_{date}T140948_P05023_N_F_J_001.h5"
        with h5py.File(os.path.join(folder, name), "w") as h:
            g = h.create_group("/science/LSAR/GCOV/grids/frequencyA")
            g.create_dataset("HHHH", data=hh_p, chunks=(512, 512), compression="gzip", compression_opts=1)
            g.create_dataset("HVHV", data=hv_p, chunks=(512, 512), compression="gzip", compression_opts=1)
            g.create_dataset("xCoordinates", data=x)
            g.create_dataset("yCoordinates", data=y)
            g.create_dataset("projection", data=np.uint32(epsg)).attrs["epsg_code"] = epsg
        truth[f"{date[:4]}-{date[4:6]}-{date[6:]}"] = float(water.sum() * 0.0004)
    return truth


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(os.path.join(WORK, "scenes"))
    cells = [c.source for c in nbformat.read(NOTEBOOK, as_version=4).cells if c.cell_type == "code"]
    ns, truth = {}, None
    for src in cells:
        if src.startswith("!pip") or "earthaccess.login()" in src:
            continue                                                      # no installation, no NASA login
        if "SCENES = find_scenes(tracks)" in src:                         # instead of the NASA search: the fake scenes
            print("Building 11 simulated scenes (about a minute)...")
            truth = simulate(ns, os.path.join(WORK, "scenes"))
            scenes = []
            for f in sorted(glob.glob(os.path.join(WORK, "scenes", "*.h5"))):
                i = ns["parse_name"](os.path.basename(f))
                d = i["start"][:8]
                scenes.append(dict(url=f, date=f"{d[:4]}-{d[4:6]}-{d[6:]}", time_utc=i["start"], track=i["track"], dir=i["dir"],
                                   frame=i["frame"], mode=i["mode"], pol=i["pol"], crid=i["crid"], collection="SIMULATED"))
            ns.update(SCENES=scenes, OPENER=lambda url: h5py.File(url, "r"), OUT=os.path.join(WORK, "out"))
            ns["plt"].show = lambda *a, **k: None
            continue
        if "zipfile.ZipFile" in src:
            continue                                                      # no export needed for the check
        exec(src, ns)

    print("\nSimulated scenes: measured area against the truth")
    errors = []
    for r in ns["rows"]:
        e = r["area_km2"] - truth[r["date"]]
        errors.append(e)
        print(f"  {r['date']}   measured {r['area_km2']:7.2f} km2   truth {truth[r['date']]:7.2f} km2   error {e:+.2f}")
    rise = max(r["area_km2"] for r in ns["rows"]) - ns["rows"][0]["area_km2"]
    true_rise = max(truth.values()) - truth[ns["rows"][0]["date"]]
    worst = max(errors, key=abs)
    print(f"\nRise since the first date: measured {rise:+.2f} km2, truth {true_rise:+.2f} km2")
    print(f"Mean error {sum(abs(e) for e in errors) / len(errors):.2f} km2, worst {worst:+.2f} km2")
    shutil.rmtree(WORK, ignore_errors=True)
    if abs(worst) > 2.0:
        sys.exit("CHECK FAILED: an error above 2 km2")
    print("CHECK PASSED")


if __name__ == "__main__":
    main()
