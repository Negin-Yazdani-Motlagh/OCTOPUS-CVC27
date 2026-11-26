#!/bin/bash
# Private Bouchet probe. Runs in the login account home, not PI scratch.
set -u
source /etc/profile >/dev/null 2>&1 || true
umask 077

BASE="${HOME}/.cs_p2"
mkdir -p "${BASE}/logs" "${BASE}/assets" "${BASE}/data"
chmod 700 "${BASE}" "${BASE}/logs" "${BASE}/assets" "${BASE}/data"
LOG="${BASE}/logs/probe.txt"
exec > >(tee "${LOG}") 2>&1

echo "DATE $(date -Is 2>/dev/null || date)"
echo "USER ${USER}"
echo "HOME ${HOME}"
echo "BASE ${BASE}"
id
echo "---- permissions ----"
ls -ld "${HOME}" "${BASE}"
namei -l "${BASE}" 2>/dev/null || true
echo "---- quota ----"
quota -s || true
command -v getquota >/dev/null && getquota || true
df -h "${HOME}"
avail_kb=$(df -Pk "${HOME}" | awk 'NR==2 {print $4}')
echo "HOME_AVAIL_KB ${avail_kb:-unknown}"
echo "---- python ----"
python3 --version || true
echo "---- modules ----"
if command -v module >/dev/null 2>&1; then
  module -t avail cuda 2>&1 | head -60 || true
  echo "---- python modules ----"
  module -t avail python 2>&1 | head -30 || true
else
  echo "module command missing"
fi
echo "---- accounts ----"
sacctmgr -nP show assoc user="${USER}" format=Account,Partition,QOS 2>/dev/null | head -40 || true
echo "---- sinfo ----"
sinfo -o "%P %G %D %a %l" | head -80

echo "---- gpu probe ----"
part=$(sinfo -h -o "%P %G %a" | awk 'BEGIN{IGNORECASE=1} $2 ~ /gpu/ && $3 ~ /up|mix|idle/ { gsub(/\*$/,"",$1); print $1; exit }')
acct=$(sacctmgr -nP show assoc user="${USER}" format=Account 2>/dev/null | awk 'NF && !seen[$0]++ { print; exit }')
echo "CHOSEN_PARTITION ${part:-none}"
echo "CHOSEN_ACCOUNT ${acct:-none}"
if [ -n "${part:-}" ]; then
  srun_args=(--job-name=check --partition="${part}" --gpus=1 --cpus-per-task=2 --mem=8G --time=00:05:00)
  if [ -n "${acct:-}" ]; then
    srun_args+=(--account="${acct}")
  fi
  timeout 180 srun "${srun_args[@]}" bash -lc 'echo GPU_NODE $(hostname); nvidia-smi --query-gpu=name,compute_cap,memory.total,driver_version --format=csv; echo NVCC; nvcc --version || true; echo PY; python3 --version || true' || echo "GPU_PROBE_FAILED"
else
  echo "NO_GPU_PARTITION_PARSED"
fi

echo "---- downloads ----"
if [ "${avail_kb:-0}" -gt 8000000 ]; then
  curl -L --fail --retry 3 --continue-at - \
    -o "${BASE}/assets/bevfusion_single_lidar.py" \
    "https://huggingface.co/cisl-hf/CooperScene/resolve/main/bevfusion/bevfusion_single_lidar.py" \
    && wc -c "${BASE}/assets/bevfusion_single_lidar.py" \
    || echo "CONFIG_DOWNLOAD_FAILED"
  curl -L --fail --retry 3 --continue-at - \
    -o "${BASE}/assets/bevfusion_single_lidar.pth" \
    "https://huggingface.co/cisl-hf/CooperScene/resolve/main/bevfusion/bevfusion_single_lidar.pth" \
    && wc -c "${BASE}/assets/bevfusion_single_lidar.pth" \
    && sha256sum "${BASE}/assets/bevfusion_single_lidar.pth" \
    || echo "CHECKPOINT_DOWNLOAD_FAILED"
  echo "EXPECTED_CHECKPOINT_BYTES 115390760"
else
  echo "SKIP_DOWNLOADS home free space below 8GB"
fi

if [ "${avail_kb:-0}" -gt 45000000 ]; then
  echo "MINI_ZIP_START"
  curl -L --fail --retry 3 --continue-at - \
    -o "${BASE}/data/mini.zip" \
    "https://data.ucr.edu/datasets/cooperscene/mini.zip" \
    && ls -lh "${BASE}/data/mini.zip" \
    && sha256sum "${BASE}/data/mini.zip" \
    || echo "MINI_DOWNLOAD_FAILED"
else
  echo "SKIP_MINI_ZIP home free space below 45GB"
fi

echo "DONE"
echo "LOG ${LOG}"
