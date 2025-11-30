#!/usr/bin/env python3
"""
detect_and_pose_pnp.py
Minimal template showing how to use solvePnP given correspondences.
This is an example — you must supply your own 2D-3D matches.
"""
import argparse
import cv2
import numpy as np
from utils import load_camera_params, draw_axes
import os

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera-file", required=True)
    ap.add_argument("--image", required=True)
    args = ap.parse_args()

    K, dist, _ = load_camera_params(args.camera_file)
    img = cv2.imread(args.image)
    if img is None:
        print("Failed to load image"); return

    # === USER: replace these with your own correspondences ===
    # Example: a square of size 0.1 m on plane z=0:
    model_points = np.array([
        [0.0, 0.0, 0.0],
        [0.1, 0.0, 0.0],
        [0.1, 0.1, 0.0],
        [0.0, 0.1, 0.0]
    ], dtype=np.float32)

    # Detect 2D points in the image (must correspond to model_points order)
    # For demo: you could use manual clicking or a simple corner detector
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    corners = cv2.goodFeaturesToTrack(gray, maxCorners=4, qualityLevel=0.01, minDistance=10)
    if corners is None or len(corners) < 4:
        print("Need 4 detected image points for demo. Found:", 0 if corners is None else len(corners))
        return
    image_points = np.squeeze(corners[:4]).astype(np.float32)

    # Solve PnP
    retval, rvec, tvec = cv2.solvePnP(model_points, image_points, K, dist, flags=cv2.SOLVEPNP_ITERATIVE)
    if not retval:
        print("solvePnP failed"); return
    print("tvec (m):", tvec.ravel())
    annotated = img.copy()
    # draw image points
    for p in image_points:
        cv2.circle(annotated, tuple(p.astype(int)), 5, (0,255,0), -1)
    annotated = draw_axes(annotated, K, dist, rvec, tvec, axis_length=0.05)
    os.makedirs("outputs", exist_ok=True)
    outpath = "outputs/pnp_pose.jpg"
    cv2.imwrite(outpath, annotated)
    print("Saved:", outpath)

if __name__ == "__main__":
    main()
