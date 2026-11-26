#!/bin/bash
# B200 smoke setup for the CooperScene single-agent LiDAR checkpoint.
# Does not train, does not run the full split, does not use a cooperative checkpoint.
# Delete the work directory when finished:
#   rm -rf /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2
echo "SCRIPT_START $(date)"
set +u
source /etc/profile
set +u

ROOT=/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2
mkdir -p "$ROOT"/{src,assets,data,logs,venv,tmp}
chmod 700 "$ROOT"
exec > >(tee -a "$ROOT/logs/install.txt") 2>&1

echo "DATE $(date)"
echo "HOST $(hostname)"
df -h "$ROOT" /tmp "$HOME"

if df -Pk /tmp | awk 'NR==2 {exit !($4+0 > 30000000)}'; then
  export TMPDIR=/tmp/cs_p2
else
  export TMPDIR="$ROOT/tmp"
fi
mkdir -p "$TMPDIR"
export PIP_CACHE_DIR="$TMPDIR/pip"
mkdir -p "$PIP_CACHE_DIR"
export TORCH_CUDA_ARCH_LIST=10.0
export FORCE_CUDA=1
export MMCV_WITH_OPS=1
export MAX_JOBS=4
export PYTHONNOUSERSITE=1

module purge
module load PyTorch/2.9.1-foss-2024a-CUDA-12.8.0
hash -r
echo "PYTHON $(command -v python) $(python -V 2>&1)"
echo "NVCC $(command -v nvcc || echo missing)"
nvcc --version || { echo "NVCC_MISSING"; exit 1; }
echo "CUDA_HOME ${CUDA_HOME:-unset}"
echo "CXX $(command -v g++)"

python - << 'PY'
import torch
print("torch", torch.__version__)
print("torch_cuda", torch.version.cuda)
print("capability", torch.cuda.get_device_capability())
print("device", torch.cuda.get_device_name(0))
y = torch.zeros(4, device="cuda")
print("cuda_tensor_ok", y.device)
PY

python -m venv --system-site-packages "$ROOT/venv"
# shellcheck disable=SC1091
source "$ROOT/venv/bin/activate"
python -m pip install -U pip "setuptools<81" wheel

if [ ! -d "$ROOT/src/CooperScene/.git" ]; then
  git clone --depth 1 https://github.com/UCR-CISL/CooperScene.git "$ROOT/src/CooperScene"
fi

python - << PY
from pathlib import Path
p = Path("$ROOT/src/CooperScene/models/bevfusion/setup.py")
text = p.read_text()
old = "'-gencode=arch=compute_86,code=sm_86',"
new = old + "\n                '-gencode=arch=compute_90,code=sm_90',\n                '-gencode=arch=compute_100,code=sm_100',"
if "compute_100" not in text:
    if old not in text:
        raise SystemExit("setup.py arch pattern missing")
    p.write_text(text.replace(old, new, 1))
    print("PATCHED_BEVFUSION_ARCH")
else:
    print("BEVFUSION_ARCH_ALREADY_PATCHED")
PY

python -m pip install mmengine einops tqdm pyyaml shapely packaging huggingface_hub opencv-python-headless
python -m pip install open3d || echo "OPEN3D_FAILED"

PYTAG=$(python - << 'PY'
import sys
print(f"cp{sys.version_info.major}{sys.version_info.minor}")
PY
)
echo "PYTAG $PYTAG"
python -m pip install \
  "https://github.com/fafraob/spconv-wheels/releases/download/v2.3.8/cumm_cu128-0.8.2-${PYTAG}-${PYTAG}-linux_x86_64.whl" \
  "https://github.com/fafraob/spconv-wheels/releases/download/v2.3.8/spconv_cu128-2.3.8-${PYTAG}-${PYTAG}-linux_x86_64.whl"
python - << 'PY'
import torch, spconv
print("spconv", spconv.__version__)
PY

if ! python -m pip install "mmcv==2.2.0+cu.12.8.torch.2.9" --extra-index-url https://wheels.astral.sh/simple/cu128/; then
  echo "ASTRAL_MMCV_WHEEL_FAILED building mmcv v2.2.0 from source"
  if [ ! -d "$ROOT/src/mmcv/.git" ]; then
    git clone --depth 1 --branch v2.2.0 https://github.com/open-mmlab/mmcv.git "$ROOT/src/mmcv"
  fi
  python -m pip install -r "$ROOT/src/mmcv/requirements/optional.txt"
  python -m pip install --no-build-isolation "$ROOT/src/mmcv"
fi
python - << 'PY'
import mmcv, mmcv._ext
print("mmcv", mmcv.__version__)
PY

python -m pip install --no-deps "mmdet==3.3.0" "mmdet3d==1.4.0" || \
  MMCV_WITH_OPS=1 python -m pip install --no-build-isolation --no-deps "mmdet==3.3.0" "mmdet3d==1.4.0"

cd "$ROOT/src/CooperScene"
export PYTHONPATH="$ROOT/src/CooperScene${PYTHONPATH:+:$PYTHONPATH}"
python models/bevfusion/setup.py build_ext --inplace

python - << 'PY'
from huggingface_hub import hf_hub_download
names = [
    "bevfusion/bevfusion_single_lidar.py",
    "bevfusion/bevfusion_single_lidar.pth",
]
for name in names:
    path = hf_hub_download("cisl-hf/CooperScene", name, local_dir="assets")
    print("DOWNLOADED", path)
PY

python - << 'PY'
import hashlib
from pathlib import Path
p = Path("assets/bevfusion/bevfusion_single_lidar.pth")
size = p.stat().st_size
h = hashlib.sha256()
with p.open("rb") as handle:
    for chunk in iter(lambda: handle.read(1 << 20), b""):
        h.update(chunk)
print("CHECKPOINT_BYTES", size)
print("CHECKPOINT_SHA256", h.hexdigest())
print("EXPECTED_BYTES 115390760")
print("EXPECTED_SHA256 d71292a772a3f422eb818ab5012a893ee325bffef572524f9c89681eea50f761")
PY

python - << 'PY'
import torch
from mmdet3d.apis import init_model
cfg = "assets/bevfusion/bevfusion_single_lidar.py"
ckpt = "assets/bevfusion/bevfusion_single_lidar.pth"
model = init_model(cfg, ckpt, device="cuda:0")
weight = next(model.parameters())
print("MODEL_LOAD_OK", type(model).__name__, weight.device, weight.dtype)
print("CUDA_MEM_MIB", round(torch.cuda.memory_allocated() / 1048576, 1))
PY

if [ ! -f "$ROOT/data/mini.zip" ]; then
  curl -L --fail --retry 3 -o "$ROOT/data/mini.zip" https://data.ucr.edu/datasets/cooperscene/mini.zip
fi
python - << PY
import zipfile
from pathlib import Path
zpath = Path("$ROOT/data/mini.zip")
out = Path("$ROOT/data/mini")
out.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(zpath) as zf:
    zf.extractall(out)
print("UNZIPPED", zpath, "bytes", zpath.stat().st_size)
PY

python - << PY
from pathlib import Path
root = Path("$ROOT/data/mini")
candidates = [root, *([p for p in root.iterdir() if p.is_dir()] if root.is_dir() else [])]
base = next((p for p in candidates if all((p / s).is_dir() for s in ("train", "validate", "test"))), None)
print("DATA_ROOT", base)
if base is None:
    raise SystemExit("MINI_LAYOUT_NOT_FOUND")
for split, expected in (("train", 120), ("validate", 30), ("test", 30)):
    takes = [p for p in (base / split).iterdir() if p.is_dir()]
    agents = {}
    frames = {}
    for agent in ("0", "1", "2", "3"):
        pcds = list((base / split).glob(f"*/{agent}/*.pcd"))
        yamls = [p for p in (base / split).glob(f"*/{agent}/*.yaml") if not p.name.endswith("_additional.yaml") and not p.name.endswith("_separate.yaml")]
        agents[agent] = len({p.parent.parent.name for p in pcds})
        frames[agent] = len(pcds)
        print(f"{split} agent {agent} takes {agents[agent]} pcd {len(pcds)} yaml {len(yamls)}")
    print(f"{split} expected_frames {expected}")
print("STRUCTURE_OK")
print(base)
Path("$ROOT/logs/data_root.txt").write_text(str(base))
PY

DATA_ROOT=$(cat "$ROOT/logs/data_root.txt")
python - << PY
import traceback
from pathlib import Path
root = Path("$DATA_ROOT")
pcd = next(root.glob("test/*/1/*.pcd"))
print("ONE_FRAME", pcd)
try:
    from mmdet3d.apis import init_model, inference_detector
    model = init_model(
        "assets/bevfusion/bevfusion_single_lidar.py",
        "assets/bevfusion/bevfusion_single_lidar.pth",
        device="cuda:0",
    )
    result = inference_detector(model, str(pcd))
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

echo "DONE"
echo "LOG $ROOT/logs/install.txt"
echo "DELETE_LATER rm -rf $ROOT"
