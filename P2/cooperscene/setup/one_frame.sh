#!/bin/bash
echo "SCRIPT_START $(date)"
set +u
source /etc/profile
module load PyTorch/2.9.1-foss-2024a-CUDA-12.8.0
unset LD_PRELOAD
hash -r
source /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/venv/bin/activate
hash -r
export PYTHONNOUSERSITE=1
export PYTHONPATH=/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/src/CooperScene
if [ -n "${LD_LIBRARY_PATH:-}" ]; then
  LD_LIBRARY_PATH=$(printf '%s\n' "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -v '/PyTorch/' | paste -sd ':' -)
  export LD_LIBRARY_PATH
fi
TORCHLIB=$(python -c "import os,torch; print(os.path.join(os.path.dirname(torch.__file__), 'lib'))")
export LD_LIBRARY_PATH="$TORCHLIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/src/CooperScene
python - << 'PY'
import traceback
import numpy as np
import torch
from mmengine.config import Config
from mmdet3d.apis import init_model, inference_detector

pcd_path = "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/data/mini/mini/test/1/1/481410.pcd"
cfg_path = "assets/bevfusion/bevfusion_single_lidar.py"
ckpt_path = "assets/bevfusion/bevfusion_single_lidar.pth"

def read_pcd(path):
    import open3d as o3d
    cloud = o3d.t.io.read_point_cloud(path)
    xyz = cloud.point["positions"].numpy().astype(np.float32)
    intensity = None
    for key in ("intensity", "intensities"):
        if key in cloud.point:
            intensity = cloud.point[key].numpy().astype(np.float32).reshape(-1, 1)
            break
    if intensity is None:
        intensity = np.zeros((xyz.shape[0], 1), dtype=np.float32)
    return np.concatenate([xyz, intensity], axis=1)

def find_load_dim(cfg):
    pipelines = []
    for key in ("test_pipeline", "test_dataloader"):
        if key in cfg:
            pipelines.append(cfg[key])
    found = []
    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "LoadPointsFromFile":
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)
    walk(pipelines)
    if not found:
        return 4
    return int(found[0].get("load_dim", 4))

try:
    cfg = Config.fromfile(cfg_path)
    load_dim = find_load_dim(cfg)
    print("LOAD_DIM", load_dim)
    points = read_pcd(pcd_path)
    print("PCD_POINTS", points.shape[0], "FIELDS", points.shape[1])
    if points.shape[1] < load_dim:
        pad = np.zeros((points.shape[0], load_dim - points.shape[1]), dtype=np.float32)
        points = np.concatenate([points, pad], axis=1)
    elif points.shape[1] > load_dim:
        points = points[:, :load_dim]
    bin_path = "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/data/one_frame.bin"
    points.astype(np.float32).tofile(bin_path)
    print("BIN_BYTES", points.nbytes)

    _load = torch.load
    def _trusted_load(*args, **kwargs):
        kwargs["weights_only"] = False
        return _load(*args, **kwargs)
    torch.load = _trusted_load

    model = init_model(cfg_path, None, device="cuda:0")
    blob = torch.load(ckpt_path, map_location="cpu")
    state = blob.get("state_dict", blob)
    model_state = model.state_dict()
    permuted = 0
    mismatched = []
    fixed = {}
    for key, value in state.items():
        target = key[7:] if key.startswith("module.") else key
        if target not in model_state:
            continue
        want = model_state[target].shape
        if tuple(value.shape) == tuple(want):
            fixed[target] = value
        elif value.ndim == 5 and tuple(value.permute(1, 2, 3, 4, 0).shape) == tuple(want):
            fixed[target] = value.permute(1, 2, 3, 4, 0).contiguous()
            permuted += 1
        else:
            mismatched.append((target, tuple(value.shape), tuple(want)))
    missing, unexpected = model.load_state_dict(fixed, strict=False)
    print("PERMUTED_WEIGHTS", permuted)
    print("STILL_MISMATCHED", len(mismatched))
    for item in mismatched[:8]:
        print("MISMATCH", item)
    print("MISSING_KEYS", len(missing))
    model.eval()
    with torch.no_grad():
        result = inference_detector(model, bin_path)
    print("MODEL_LOAD_OK", type(model).__name__)
    print("ONE_FRAME_OK", type(result).__name__)
    pred = getattr(result, "pred_instances_3d", None)
    if pred is not None and hasattr(pred, "scores_3d"):
        print("BOXES", int(len(pred.scores_3d)))
        if len(pred.scores_3d):
            print("MAX_SCORE", float(pred.scores_3d.max()))
except Exception:
    traceback.print_exc()
    print("ONE_FRAME_FAILED")
PY
echo DONE
