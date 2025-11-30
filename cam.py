# cam.py
import numpy as np
from pathlib import Path
Path("outputs").mkdir(parents=True, exist_ok=True)
# synthetic intrinsics (change fx/cx if you want)
K = np.array([[800., 0., 320.],
              [0., 800., 240.],
              [0.,   0.,   1.]])
dist = np.zeros(5)
np.savez("outputs/camera.npz", K=K, dist=dist, reproj_err=0.0)
print("Saved outputs/camera.npz (synthetic)")
