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
case "$TORCHLIB" in
  /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/venv/*) ;;
  *) echo "TORCH_STILL_FROM_MODULE $TORCHLIB"; exit 1 ;;
esac
export LD_LIBRARY_PATH="$TORCHLIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export VALIDATION_OUT=/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/validation_inference
python -c "import shapely, scipy" || python -m pip install shapely scipy
cd /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/src/CooperScene
python /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/validation_inference/run_validation_inference.py
echo DONE
