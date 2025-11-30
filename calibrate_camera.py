# calibrate_aruco.py
# Usage:
# python calibrate_aruco.py --images "samples/*.jpg" --dictionary DICT_6X6_250 --out outputs/camera_aruco.npz
import argparse
import glob
from pathlib import Path
import cv2
import numpy as np

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--images", type=str, required=True)
    p.add_argument("--dictionary", type=str, default="DICT_6X6_250",
                   help="ArUco dictionary (DICT_4X4_50 / DICT_5X5_100 / DICT_6X6_250 etc.)")
    p.add_argument("--out", type=str, default="outputs/camera_aruco.npz")
    return p.parse_args()

def main():
    args = parse_args()
    imgs = sorted(glob.glob(args.images))
    if not imgs:
        raise SystemExit("No images matched pattern")
    dict_name = args.dictionary
    aruco_dict = getattr(cv2.aruco, dict_name)
    dictionary = cv2.aruco.Dictionary_get(aruco_dict)
    params = cv2.aruco.DetectorParameters_create()

    all_corners = []
    all_ids = []
    img_size = None

    for pth in imgs:
        im = cv2.imread(pth)
        if im is None:
            continue
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        img_size = (gray.shape[1], gray.shape[0])
        corners, ids, _ = cv2.aruco.detectMarkers(gray, dictionary, parameters=params)
        if ids is not None and len(ids) > 0:
            all_corners.append(corners)
            all_ids.append(ids)
            print(f"Found {len(ids)} markers in {pth}")
        else:
            print(f"No markers in {pth}")

    if not all_corners:
        raise SystemExit("No ArUco markers detected in any image.")

    flags = cv2.CALIB_RATIONAL_MODEL
    ret, K, dist, rvecs, tvecs = cv2.aruco.calibrateCameraAruco(
        all_corners, all_ids, np.array([len(ids) for ids in all_ids]), dictionary, img_size, None, None
    )
    reproj_err = 0.0
    Path("outputs").mkdir(parents=True, exist_ok=True)
    np.savez(args.out, K=K, dist=dist, reproj_err=reproj_err)
    print("Saved:", args.out)

if __name__ == "__main__":
    main()
