#!/usr/bin/env python3
"""
detect_and_pose_aruco_debug.py
Robust debug tool for ArUco detection + pose on a single image (or webcam if you change source).
- Tries multiple dictionaries
- Saves contrast-enhanced and threshold debug images
- Prints which dictionary found markers and saves annotated images
Usage:
    python detect_and_pose_aruco_debug.py --image samples/aruco_sample.jpg --camera outputs/camera.npz --out outputs/aruco_debug_out.jpg
"""
import argparse
import cv2
import numpy as np
from pathlib import Path
import sys
import os

def load_camera_params(path):
    p = Path(path)
    if not p.exists():
        print(f"[WARN] Camera file {path} not found. Using synthetic intrinsics (detection-only).")
        # synthetic intrinsics (cx/cy chosen for 640x480 typical frame)
        K = np.array([[800., 0., 320.],
                      [0., 800., 240.],
                      [0.,   0.,   1.]])
        dist = np.zeros(5)
        return K, dist
    data = np.load(str(p))
    K = data.get("K")
    dist = data.get("dist", np.zeros(5))
    if K is None:
        raise RuntimeError("camera npz missing K")
    return K, dist

def draw_axes_simple(img, K, dist, rvec, tvec, length=0.05):
    """Draw X (red), Y (green), Z (blue) axes on img. rvec,tvec must be (3,1) or (3,)"""
    img = img.copy()
    axis = np.float32([[length,0,0],[0,length,0],[0,0,length]]).reshape(-1,3)
    origin = np.float32([[0,0,0]]).reshape(-1,3)
    imgpts_o, _ = cv2.projectPoints(origin, rvec, tvec, K, dist)
    imgpts_axis, _ = cv2.projectPoints(axis, rvec, tvec, K, dist)
    o = tuple(int(x) for x in imgpts_o[0].ravel())
    colors = [(0,0,255),(0,255,0),(255,0,0)]
    for pt, col in zip(imgpts_axis.reshape(-1,2), colors):
        p = tuple(int(x) for x in pt.ravel())
        cv2.line(img, o, p, col, 2)
    cv2.circle(img, o, 4, (0,255,255), -1)
    return img

def try_detect_all_dicts(gray, visualize=False):
    """Try detection across common dictionaries. Return dict_name -> (corners, ids) for those with detections."""
    # common dictionaries to try
    dict_names = [
        "DICT_4X4_50", "DICT_4X4_100", "DICT_4X4_250", "DICT_4X4_1000",
        "DICT_5X5_50", "DICT_5X5_100", "DICT_5X5_250", "DICT_5X5_1000",
        "DICT_6X6_50", "DICT_6X6_100", "DICT_6X6_250", "DICT_6X6_1000",
        "DICT_7X7_50", "DICT_7X7_100", "DICT_7X7_250", "DICT_7X7_1000",
        # ARUCO original dictionaries often used
    ]
    found = {}
    # Detector parameters (try both API names)
    try:
        params = cv2.aruco.DetectorParameters_create()
    except AttributeError:
        # OpenCV builds where API differs
        try:
            params = cv2.aruco.DetectorParameters()
        except Exception:
            params = None

    for name in dict_names:
        # skip if attribute not present
        if not hasattr(cv2.aruco, name):
            continue
        aruco_dict = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, name))
        # OpenCV 4.7+ supports detectMarkers with parameters object; older versions use same function
        try:
            corners, ids, rejected = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=params)
        except Exception:
            # try fallback signature
            corners, ids, rejected = cv2.aruco.detectMarkers(gray, aruco_dict)
        if ids is not None and len(ids) > 0:
            found[name] = (corners, ids, rejected)
    return found

def enhance_contrast(img):
    """Return CLAHE-enhanced grayscale and a binary threshold for debugging."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    g = clahe.apply(gray)
    # simple adaptive threshold (helps detection if lighting is uneven)
    th = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 11, 2)
    return g, th

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="Input image path")
    ap.add_argument("--camera", default="outputs/camera.npz", help="Camera npz (K,dist) optional")
    ap.add_argument("--out", default="outputs/aruco_debug_out.jpg", help="Output annotated image")
    args = ap.parse_args()

    Path("outputs").mkdir(parents=True, exist_ok=True)

    if not Path(args.image).exists():
        print("Input image not found:", args.image); sys.exit(1)

    img = cv2.imread(str(args.image))
    if img is None:
        print("Failed to load image:", args.image); sys.exit(1)

    K, dist = load_camera_params(args.camera)
    # make sizes predictable for cx/cy if using synthetic K (but detection doesn't need that)
    h, w = img.shape[:2]

    # Save enhanced debug images
    g_clahe, th = enhance_contrast(img)
    cv2.imwrite("outputs/debug_clahe_gray.jpg", g_clahe)
    cv2.imwrite("outputs/debug_adaptive_thresh.jpg", th)
    print("Saved debug images: outputs/debug_clahe_gray.jpg, outputs/debug_adaptive_thresh.jpg")

    # Try raw grayscale first
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    found = try_detect_all_dicts(gray)
    # If none found on raw grayscale, try CLAHE grayscale and threshold
    if not found:
        print("[INFO] No markers found on raw grayscale. Trying CLAHE image...")
        found = try_detect_all_dicts(g_clahe)
    if not found:
        print("[INFO] No markers found on CLAHE. Trying adaptive-threshold image...")
        found = try_detect_all_dicts(th)

    if not found:
        print("[RESULT] No ArUco markers detected with any common dictionary.")
        print(" - Check the printed marker dictionary and match --dict in main script")
        print(" - Make sure marker is clear, high-contrast, not rotated extreme, and fills the frame.")
        # save a combined visualization so you can inspect
        vis = img.copy()
        cv2.putText(vis, "No markers detected (see outputs/debug_*.jpg)", (10,30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
        cv2.imwrite(args.out, vis)
        print("Wrote:", args.out)
        sys.exit(0)

    # If we get here, at least one dictionary found markers.
    # Pick the dictionary with the most detections
    best = max(found.items(), key=lambda kv: (kv[1][1].shape[0] if kv[1][1] is not None else 0))
    dict_name, (corners, ids, rejected) = best
    print(f"[RESULT] Detected markers using dictionary: {dict_name}. ids: {ids.flatten().tolist()}")

    annotated = img.copy()
    # draw detected markers
    try:
        cv2.aruco.drawDetectedMarkers(annotated, corners, ids)
    except Exception:
        # fallback: draw manual boxes
        for c in corners:
            pts = c.reshape(-1,2).astype(int)
            cv2.polylines(annotated, [pts], True, (0,255,0), 2)

    # estimate pose if possible (need K)
    try:
        rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(corners, 0.05, K, dist)
        for rvec, tvec, mid in zip(rvecs, tvecs, ids.flatten()):
            annotated = draw_axes_simple(annotated, K, dist, rvec.reshape(3,1), tvec.reshape(3,1), length=0.03)
            print(f"Marker {int(mid)} -> t(m): {tvec.ravel()}")
    except Exception as e:
        print("[WARN] estimatePoseSingleMarkers failed or not available:", e)

    # Save annotated image
    outpath = args.out
    cv2.imwrite(outpath, annotated)
    print("Saved annotated image to:", outpath)
    # Also save a version labelled with the dictionary
    dict_out = Path(outpath).with_name(Path(outpath).stem + f"_{dict_name}.jpg")
    cv2.imwrite(str(dict_out), annotated)
    print("Saved per-dictionary annotated image to:", dict_out)

if __name__ == "__main__":
    main()
