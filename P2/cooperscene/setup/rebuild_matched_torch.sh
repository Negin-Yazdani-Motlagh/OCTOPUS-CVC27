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
python -m pip install "torch==2.9.1" --index-url https://download.pytorch.org/whl/cu128
TORCHLIB=$(python -c "import os,torch; print(os.path.join(os.path.dirname(torch.__file__), 'lib'))")
case "$TORCHLIB" in
  /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/venv/*) ;;
  *) echo "TORCH_STILL_FROM_MODULE $TORCHLIB"; exit 1 ;;
esac
export LD_LIBRARY_PATH="$TORCHLIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python - << 'PY'
import torch
print("TORCH", torch.__version__, torch.version.cuda, torch.cuda.get_device_capability())
print("TORCH_FILE", torch.__file__)
if torch.cuda.get_device_capability() != (10, 0):
    raise SystemExit("GPU_IS_NOT_B200")
PY
export CUDA_HOME=/apps/software/system/software/CUDA/12.8.0
export TORCH_CUDA_ARCH_LIST=10.0
export FORCE_CUDA=1
export MMCV_WITH_OPS=1
export MAX_JOBS=4
cd /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/src/mmcv
rm -rf build mmcv/_ext*.so
python setup.py build_ext --inplace
python -m pip install --no-build-isolation --no-deps -e .
python - << 'PY'
import mmcv._ext
print("MMCV_EXT_OK")
PY
cd /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/src/CooperScene
python - << 'PY'
import traceback
from mmdet3d.apis import init_model, inference_detector
pcd = "/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/data/mini/mini/test/1/1/481410.pcd"
try:
    model = init_model(
        "assets/bevfusion/bevfusion_single_lidar.py",
        "assets/bevfusion/bevfusion_single_lidar.pth",
        device="cuda:0",
    )
    print("MODEL_LOAD_OK", type(model).__name__)
    result = inference_detector(model, pcd)
    print("ONE_FRAME_OK", type(result).__name__)
    pred = getattr(result, "pred_instances_3d", None)
    if pred is not None and hasattr(pred, "scores_3d"):
        print("BOXES", len(pred.scores_3d))
        if len(pred.scores_3d):
            print("MAX_SCORE", float(pred.scores_3d.max()))
except Exception:
    traceback.print_exc()
    print("ONE_FRAME_FAILED")
PY
echo DONE
