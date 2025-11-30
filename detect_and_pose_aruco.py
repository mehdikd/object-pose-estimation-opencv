#!/usr/bin/env python3
"""
detect_and_pose_aruco.py
Usage:
python detect_and_pose_aruco.py --camera-file outputs/camera.npz --source samples/aruco_sample.jpg --out outputs/aruco_out.jpg
python detect_and_pose_aruco.py --camera-file outputs/camera.npz --source 0
"""
import argparse, os
import cv2, numpy as np
from utils import load_camera_params, draw_axes

def create_detector_params():
    if hasattr(cv2.aruco, "DetectorParameters_create"):
        return cv2.aruco.DetectorParameters_create()
    else:
        return cv2.aruco.DetectorParameters()

def get_aruco_dictionary(dict_name):
    try:
        dict_id = getattr(cv2.aruco, dict_name)
    except AttributeError:
        raise SystemExit(f"Unknown ArUco dictionary: {dict_name}")
    try:
        return cv2.aruco.getPredefinedDictionary(dict_id)
    except Exception:
        try:
            return cv2.aruco.Dictionary_get(dict_id)
        except Exception:
            return cv2.aruco.Dictionary(dict_id)

def process_frame(frame, aruco_dict, params, K, dist, marker_size, out_draw=True):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    try:
        corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=params)
    except Exception:
        corners, ids = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=params)
    if ids is not None and len(ids) > 0:
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        # estimate pose per marker
        rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(corners, marker_size, K, dist)
        for rvec, tvec, mid in zip(rvecs, tvecs, ids.flatten()):
            if out_draw:
                frame = draw_axes(frame, K, dist, rvec.reshape(3,1), tvec.reshape(3,1), axis_length=marker_size*0.5)
            tv = tvec.reshape(3)
            rv = rvec.reshape(3)
            print(f"Marker {int(mid)} -> t(m): {tv[0]:.3f},{tv[1]:.3f},{tv[2]:.3f}")
    return frame

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera-file", required=True)
    ap.add_argument("--source", default=0, help="0 for webcam or path to image/file")
    ap.add_argument("--marker-size", type=float, default=0.05, help="marker side length in meters")
    ap.add_argument("--dict", type=str, default="DICT_4X4_50")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    K, dist, _ = load_camera_params(args.camera_file)
    aruco_dict = get_aruco_dictionary(args.dict)
    params = create_detector_params()

    if str(args.source).isdigit():
        cap = cv2.VideoCapture(int(args.source))
        if not cap.isOpened():
            print("Cannot open camera", args.source); return
        print("Press 'q' to quit, 's' to save snapshot.")
        while True:
            ret, frame = cap.read()
            if not ret: break
            frame = process_frame(frame, aruco_dict, params, K, dist, args.marker_size)
            cv2.imshow("ArUco Pose (press q to quit)", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"): break
            if key == ord("s"):
                os.makedirs("outputs", exist_ok=True)
                path = f"outputs/aruco_snap_{np.random.randint(0,1e6)}.jpg"
                cv2.imwrite(path, frame)
                print("Saved", path)
        cap.release()
        cv2.destroyAllWindows()
    else:
        img = cv2.imread(args.source)
        if img is None:
            print("Failed to load", args.source); return
        out_img = process_frame(img, aruco_dict, params, K, dist, args.marker_size, out_draw=True)
        if args.out:
            os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
            cv2.imwrite(args.out, out_img)
            print("Saved annotated image to", args.out)
        else:
            cv2.imshow("ArUco Pose", out_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
