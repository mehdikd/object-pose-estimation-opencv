#!/usr/bin/env python3
# calibrate_aruco.py
"""
Run:
python calibrate_aruco.py --images "samples/*.jpg" --dictionary DICT_6X6_250 --out outputs/camera.npz
"""

import argparse, glob
from pathlib import Path
import cv2
import numpy as np

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--images", required=True, help='Glob like "samples/*.jpg"')
    p.add_argument("--dictionary", default="DICT_6X6_250",
                   help="ArUco dictionary name (e.g. DICT_4X4_50, DICT_6X6_250)")
    p.add_argument("--out", default="outputs/camera.npz")
    return p.parse_args()

def get_aruco_dictionary(dict_name):
    if not hasattr(cv2, "aruco"):
        raise SystemExit("cv2.aruco not available. Install opencv-contrib-python.")
    # try common access patterns
    try:
        dict_id = getattr(cv2.aruco, dict_name)
    except AttributeError:
        raise SystemExit(f"Unknown dictionary constant: {dict_name}")
    # prefer getPredefinedDictionary (newer)
    try:
        return cv2.aruco.getPredefinedDictionary(dict_id)
    except Exception:
        # fallback older API
        try:
            return cv2.aruco.Dictionary_get(dict_id)
        except Exception:
            # last-resort: try direct constructor (rare)
            return cv2.aruco.Dictionary(dict_id)

def create_detector_params():
    # handle name difference across OpenCV builds
    if hasattr(cv2.aruco, "DetectorParameters_create"):
        return cv2.aruco.DetectorParameters_create()
    else:
        # older style
        return cv2.aruco.DetectorParameters()

def main():
    args = parse_args()
    images = sorted(glob.glob(args.images))
    if not images:
        raise SystemExit("No images matched: " + args.images)
    dictionary = get_aruco_dictionary(args.dictionary)
    params = create_detector_params()

    all_corners = []
    all_ids = []
    marker_counts = []
    img_size = None

    for pth in images:
        im = cv2.imread(pth)
        if im is None:
            print("Skipping unreadable:", pth); continue
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        img_size = (gray.shape[1], gray.shape[0])
        try:
            corners, ids, _ = cv2.aruco.detectMarkers(gray, dictionary, parameters=params)
        except Exception:
            # some builds return 2 values
            corners, ids = cv2.aruco.detectMarkers(gray, dictionary, parameters=params)
        if ids is not None and len(ids) > 0:
            all_corners.append(corners)
            all_ids.append(ids)
            marker_counts.append(len(ids))
            print(f"Found {len(ids)} markers in {pth}")
        else:
            print("No markers in", pth)

    if not all_corners:
        raise SystemExit("No ArUco markers detected in any image. Use more images or ensure the board matches dictionary.")

    markerCounterPerFrame = np.array(marker_counts, dtype=np.int32)

    # calibrate
    flags = cv2.CALIB_RATIONAL_MODEL
    try:
        ret, K, dist, rvecs, tvecs = cv2.aruco.calibrateCameraAruco(
            all_corners, all_ids, markerCounterPerFrame, dictionary, img_size, None, None, flags=flags
        )
    except Exception as e:
        raise SystemExit("calibrateCameraAruco failed: " + str(e))

    reproj_err = float(ret)
    Path("outputs").mkdir(parents=True, exist_ok=True)
    np.savez(args.out, K=K, dist=dist, reproj_err=reproj_err)
    print("Saved camera params to:", args.out)
    print("K:\n", K)
    print("dist:\n", dist)
    print("reproj_err:", reproj_err)

if __name__ == "__main__":
    main()
