# P2 setup: CooperScene single-agent LiDAR smoke test

Date: 25 November 2026.  
Machine: Yale Bouchet, node `a1117u29n01`.  
Account: `ei235`, project `pi_sjf37`.

This folder records the first real run of the published CooperScene single-agent LiDAR detector. It is the setup step in `../PLAN.md` and the CooperScene item in Section 6 of `Octopus-main/docs/RESEARCH_GUIDE.md`. Section 6 treats real three-vehicle predictions as a later extension. This step only checks that the published single-car model can be installed and run.

## Result

The published checkpoint runs on one real CooperScene scan from car 1. It returned 200 boxes. The highest score is **0.07626160234212875**.

That number is below a normal detection cutoff. The 200 boxes are the proposals the head is willing to emit, not 200 confirmed vehicles. The point cloud is in the car’s lidar frame. Intensity values on this scan run from 3 to 2855, which is a plausible reason the scores stay near 0.08.

The roadside sensor (agent 0) was not used. No cooperative or fused checkpoint was used. OCTOPUS source was not edited. Nothing was trained. `tools/test.py` was not run on the dataset.

## What this step did

1. Confirmed the local Windows laptop cannot run the official detector.
2. Confirmed the official CooperScene pins cannot run on the Bouchet B200.
3. Built a scratch environment that can import the CUDA ops and BEVFusion on that GPU.
4. Downloaded only the CooperScene mini archive and `bevfusion_single_lidar`.
5. Checked the archive layout and the checkpoint hash.
6. Ran one agent-1 test frame through the loaded model.

## What this step did not do

- Three separate vehicle JSONL files, a frozen score cutoff, or a world-XY grid.
- `scripts/run_three_vehicle_real_study.py prepare` or `evaluate`.
- Training, a full-split evaluation, or any use of agent 0 as a vehicle.
- Download of `bevfusion_coop_lidar`, `bevfusion_single_lidarcam`, or the six cooperative detectors.
- Edits to `Octopus-main`.

## Hardware

| Item | Value |
|---|---|
| GPU | NVIDIA B200, compute capability 10.0 |
| Memory | 183359 MiB |
| Driver | 580.178.04 (`nvidia-smi` reports CUDA 13.0) |
| Allocation | `srun --partition=gpu_devel --gpus=b200:1 --cpus-per-task=8 --mem=32G --time=06:00:00 --pty bash` |
| Started | about 17:18 EST on 25 Nov 2026, so the six-hour slot ends about 23:18 EST |
| Work directory | `/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2` (mode 700) |

The laptop cannot host this detector: Windows 11, RTX 3050 Laptop with 4 GB, compute capability 8.6, no `nvcc`, and a BEV grid of 1440×1440. `ENVIRONMENT.md` is an older Mac check and is not this run.

Home quota on Bouchet was 107 GiB of 125 GiB, so the install is on scratch. Scratch is visible to the `pi_sjf37` project. Delete it when the study is finished.

## Software that actually ran

The publisher’s stack is Linux, Python 3.10, PyTorch 2.1.1, CUDA 12.1, `mmcv>=2.0,<2.2`, `spconv-cu120`, and BEVFusion gencode through compute 8.6. CUDA 12.1 PTX does not JIT onto Blackwell compute 10.0. Those pins were not used.

The stack that completed the forward pass:

| Piece | Version |
|---|---|
| Compilers and CUDA | EasyBuild module `PyTorch/2.9.1-foss-2024a-CUDA-12.8.0`, `CUDA_HOME=/apps/software/system/software/CUDA/12.8.0` |
| PyTorch used by Python | pip wheel `torch==2.9.1` from `https://download.pytorch.org/whl/cu128`, installed inside the scratch virtualenv |
| Python | 3.12 from that module |
| spconv / cumm | 2.3.8 cu128 wheels from `fafraob/spconv-wheels` (compute 10.0) |
| MMCV | 2.2.0, built from source in the virtualenv (`MMCV_WITH_OPS=1`, `TORCH_CUDA_ARCH_LIST=10.0`, `MAX_JOBS=4`) |
| mmdet / mmdet3d | 3.3.0 and 1.4.0, installed `--no-deps` |
| NumPy | 2.2.6. The pin `numpy<1.25` cannot be satisfied on Python 3.12 |

The EasyBuild PyTorch libraries must not be the ones Python links against. After `module load`, strip every `/PyTorch/` entry from `LD_LIBRARY_PATH`, then put the virtualenv `torch/lib` first. Leave `LD_PRELOAD` unset. `bash script.sh` does not keep those variables in the parent shell, so each new shell has to repeat that setup. `one_frame.sh` and `rebuild_matched_torch.sh` contain the working preamble.

mmdet and mmdet3d refuse MMCV 2.2.0. Both installed copies had `mmcv_maximum_version` set to `'2.3.0'`. Lyft and nuScenes devkits were not installed. They are not needed for this single-lidar forward, and their old Shapely pin fails on Python 3.12.

## Downloads

| Item | Location | Check |
|---|---|---|
| Code | `/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/src/CooperScene` | clone of https://github.com/UCR-CISL/CooperScene |
| Config | `assets/bevfusion/bevfusion_single_lidar.py` | 16,968 bytes |
| Shared config base | `assets/_base_` symlink to `../configs/_base_` | required by the Hugging Face config |
| Weights | `assets/bevfusion/bevfusion_single_lidar.pth` | 115,390,760 bytes |
| SHA-256 | `d71292a772a3f422eb818ab5012a893ee325bffef572524f9c89681eea50f761` | matches the Hugging Face LFS id |
| Mini zip | `data/mini.zip` from https://data.ucr.edu/datasets/cooperscene/mini.zip | 2,918,993,095 bytes |
| Extracted root | `data/mini/mini` | the zip contains one extra `mini/` directory |

Frame counts: train 120, validate 30, test 30. Agents 0, 1, 2, and 3 are present in each split. One take id per split is expected for the mini release. The code is MIT. The data are CC BY-NC-SA 4.0.

## One-frame inference

Frame: `data/mini/mini/test/1/1/481410.pcd` (test split, take 1, agent 1).

`LoadPointsFromFile` reads a raw float32 buffer, so the PCD header cannot be passed through. Open3D read the cloud and wrote `data/one_frame.bin`.

| Measurement | Value |
|---|---|
| Points | 110,245 |
| Fields | 4: x, y, z, intensity |
| Binary size | 1,763,920 bytes |
| x | −94.06 m to 94.34 m |
| y | −88.26 m to 82.13 m |
| z | −3.16 m to 19.44 m |
| Intensity | 3 to 2855 |
| Model window | x and y −72 m to 72 m, z −5 m to 3 m, voxels 0.1 × 0.1 × 0.2 m |
| Return type | tuple of length 2 |
| Boxes | 200 |
| Highest score | 0.07626160234212875 |

The cloud is centered on the sensor. Points outside the model window are dropped. That cropping does not explain the low score: most of the sweep still falls inside x and y of ±72 m.

PyTorch 2.6 and later defaults `torch.load` to `weights_only=True`. This checkpoint pickles `mmengine` history buffers, so the load used `weights_only=False` after the hash check.

Published sparse-convolution weights are stored as `[out, depth, height, width, in]`. This spconv build expects `[depth, height, width, in, out]`. Passing the checkpoint straight into `init_model` skips those tensors and leaves the sparse encoder at random weights. The working load permutes each 5D tensor with `permute(1, 2, 3, 4, 0)` when that matches the model, then calls `load_state_dict(..., strict=False)`.

| Weight check | Count |
|---|---|
| Tensors permuted | 21 |
| Still mismatched | 0 |
| Missing keys | 0 |

The detection head’s own score threshold is 0.0, so it returns low-confidence proposals. A cutoff of 0.1, which is only the visualization default in `tools/test.py`, would drop every box from this frame. That 0.1 value is not a cutoff to freeze. Any cutoff used later has to be chosen on train or validate, not on the 30 test frames.

## Files in this folder

| File | Role |
|---|---|
| `README.md` | This result |
| `gpu_node_findings.txt` | B200, quota, and why the official pins do not run |
| `one_frame_findings.txt` | Checkpoint hash, frame counts, box count, and score |
| `cs_p2_install.sh` | First full install: clone, packages, downloads, structure check |
| `rebuild_matched_torch.sh` | Rebuild that made `import mmcv._ext` succeed |
| `one_frame.sh` | PCD-to-bin conversion, weight permute, and the successful forward pass |
| `remote_probe.sh`, `run_probe.ps1`, `send_probe.ps1` | Earlier login-node probe. Do not run `remote_probe.sh` inside an existing `srun` |

Remote logs, if the install was teed: `/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/logs/`.

## How to enter the environment again

On a login node, after Yale VPN:

```bash
ssh ei235@bouchet.ycrc.yale.edu
srun --partition=gpu_devel --gpus=b200:1 --cpus-per-task=8 --mem=32G --time=06:00:00 --pty bash
```

Then, on the GPU node, run `one_frame.sh` from this folder after it has been copied to the cluster. The script reloads the module, activates the virtualenv, fixes `LD_LIBRARY_PATH`, and repeats the one-frame forward pass. The virtualenv and the mini archive stay on NFS after the Slurm job ends. A new `srun` is required for more GPU work.

## Cleanup

Do not delete the scratch tree while more detector runs are still needed. Rebuilding MMCV on the B200 is the expensive part. When the study is finished:

```bash
rm -rf /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2
```

Optional leftovers from the failed ABI workaround, safe to remove only with that tree: `c10_shim.so` and `c10_shim.c` under the work directory. `LD_PRELOAD` must stay unset. Home leftovers `/home/ei235/.cs_p2` and `/home/ei235/.cs_p2_probe.sh` are not the working install.

## Next research step, not started

`../PLAN.md` still describes the export this smoke test does not produce: convert the mini set, run agents 1, 2, and 3 separately with the same checkpoint and three different run IDs, map boxes back to world XY, freeze one score cutoff on train or validate, and write the JSONL files that `run_three_vehicle_real_study.py` accepts. Agent 0 stays out. A fused output is not a fourth vehicle.
