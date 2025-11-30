# utils.py
import numpy as np
import cv2
from pathlib import Path
from typing import Tuple

def load_camera_params(path: str) -> Tuple[np.ndarray, np.ndarray, float]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Camera params file not found: {path}")
    data = np.load(str(path))
    K = data["K"]
    dist = data["dist"]
    reproj_err = float(data.get("reproj_err", -1.0))
    return K, dist, reproj_err

def draw_axes(image: np.ndarray, K: np.ndarray, dist: np.ndarray,
              rvec: np.ndarray, tvec: np.ndarray, length: float = 0.05, axis_length: float = None) -> np.ndarray:
    """
    Draw 3D axes given rvec/tvec on the provided image.
    Accepts either `length` (original) or `axis_length` (backwards compatibility).
    length: axis length in same units used for solvePnP (meters if marker size in meters)
    """
    # allow either parameter name
    if axis_length is not None:
        length = axis_length

    img = image.copy()
    # 3D points for axes: X=red, Y=green, Z=blue
    axis_points = np.float32([
        [length, 0, 0],  # X
        [0, length, 0],  # Y
        [0, 0, length],  # Z
    ]).reshape(-1, 3)

    origin = np.float32([[0, 0, 0]]).reshape(-1, 3)

    # project origin and axes endpoints
    imgpts_origin, _ = cv2.projectPoints(origin, rvec, tvec, K, dist)
    imgpts_axis, _ = cv2.projectPoints(axis_points, rvec, tvec, K, dist)

    o = tuple(int(v) for v in imgpts_origin[0].ravel())

    # draw each axis
    colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0)]  # BGR: X-red, Y-green, Z-blue
    for pt, col in zip(imgpts_axis.reshape(-1, 2), colors):
        p = tuple(int(v) for v in pt.ravel())
        cv2.line(img, o, p, col, 2)

    # draw origin circle
    cv2.circle(img, o, 4, (0, 255, 255), -1)
    return img

