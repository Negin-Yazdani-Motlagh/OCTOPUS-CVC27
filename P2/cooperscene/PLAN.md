# CooperScene mini execution plan

This is the plan for a later run. The mini archive and the checkpoint were not downloaded, and `Octopus-main` was not modified. Agent `0` is the roadside unit. A `V+2V` fused output is not one of the three vehicles.

## Official links

| Item | Link | Size named by the publisher |
|---|---|---|
| Mini archive | https://data.ucr.edu/datasets/cooperscene/mini.zip | About 2.9 GB. 180 frames: 120 train, 30 validate, 30 test |
| Project page | https://cisl.ucr.edu/CooperScene/ | Full set about 94.3 GB. Not part of this mini plan |
| Code | https://github.com/UCR-CISL/CooperScene | MIT code. Dataset files are CC BY-NC-SA 4.0 |
| Checkpoint repository | https://huggingface.co/cisl-hf/CooperScene | `tools/download.py` uses repo id `cisl-hf/CooperScene` |
| Single-agent LiDAR weights | https://huggingface.co/cisl-hf/CooperScene/resolve/main/bevfusion/bevfusion_single_lidar.pth | 115,390,760 bytes. The README rounds this to 115 MB |
| Matching config | https://huggingface.co/cisl-hf/CooperScene/resolve/main/bevfusion/bevfusion_single_lidar.py | 16,968 bytes |

The Hub lists LFS object id `d71292a772a3f422eb818ab5012a893ee325bffef572524f9c89681eea50f761` for that `.pth`. Recompute SHA-256 on the downloaded file before writing the importer manifest. Do not download `bevfusion_coop_lidar`, `bevfusion_single_lidarcam`, or the six cooperative detectors for this plan.

The local command that fetches the config, the shared `_base_` files, and the weights is:

```bash
python tools/download.py bevfusion_single_lidar
```

It writes `assets/bevfusion_single_lidar/bevfusion_single_lidar.py` and `assets/bevfusion_single_lidar/bevfusion_single_lidar.pth`. `huggingface_hub` is imported by that script and is not listed in `requirements.txt`.

## Installation

The documented host is Linux, Python 3.10, CUDA 12.1, and PyTorch 2.1. The Docker image is `pytorch/pytorch:2.1.1-cuda12.1-cudnn8-devel`. Its `TORCH_CUDA_ARCH_LIST` is `7.0;7.5;8.0;8.6;8.9;9.0+PTX`, so the CUDA ops are built for Volta through Hopper. A Pascal GPU is outside that list. `spconv-cu120` is the CUDA 12 sparse-convolution wheel.

`requirements.txt` pins:

- `torch>=2.0`
- `mmengine>=0.10`
- `mmcv>=2.0,<2.2`
- `mmdet>=3.2,<3.4`
- `mmdet3d>=1.4,<1.5`
- `numpy<1.25`
- `spconv-cu120`
- `shapely`, `open3d`, `einops`, `tqdm`, `pyyaml`

Local install, after the clone:

```bash
pip install -U openmim huggingface_hub
mim install -r requirements.txt
python models/bevfusion/setup.py develop
```

The Docker build runs those same pins and compiles the BEVFusion CUDA ops. This Mac is not that host. The voxel and BEV-pool ops are CUDA code, so a CPU-only machine cannot run the published inference command.

## What one official inference command does

After extraction, the single-agent converter is:

```bash
python tools/dataset_converters/data_converter.py \
  --data-root data/cooperscene --out-dir data/cooperscene --convert-pcd
```

That converter keeps agents `1`, `2`, and `3` and skips agent `0`. The source comment says agent `0` is the LiDAR-only roadside unit and is also omitted so the LiDAR-plus-camera stage does not break. Each kept sample stores `agent_id` and `ego_pose`. The pose field is `lidar_pose`, or `true_ego_pos` if the first key is absent: `[x, y, z, roll, yaw, pitch]`, with the yaw component in degrees.

Ground-truth boxes in the YAML are world coordinates: `location`, `center`, `extent` as half-sizes, and `angle` as roll, yaw, pitch in degrees. `transform_world_to_ego` subtracts the ego position and applies the inverse of the ego rotation. The stored box is `[x, y, z, dx, dy, dz, yaw]` in that vehicle's LiDAR frame. The detector then uses LiDAR coordinates, one class (`vehicle`), and this range in meters:

- x and y: −72 to 72
- z: −5 to 3
- voxel size: 0.1, 0.1, 0.2

The shipped test dataloader reads `cooperscene_infos_val.pkl`, with batch size 4. It does not read the test split unless the config is overridden. `tools/test.py` has `--score-thr` defaulting to 0.1, and that value is applied only when visualization is turned on. The detection head's own `score_threshold` is 0.0. The file also says `TODO: support fuse_conv_bn and format_only`. There is no flag that writes per-vehicle boxes.

So this command checks that the checkpoint runs. It does not produce the importer's three JSONL files:

```bash
python tools/test.py \
  assets/bevfusion_single_lidar/bevfusion_single_lidar.py \
  assets/bevfusion_single_lidar/bevfusion_single_lidar.pth
```

The config's `load_from` URL is an OpenMMLab nuScenes weight used as a training initialization. The inference weight is the CooperScene `.pth` passed on the command line.

## Three files the importer will accept

`scripts/run_three_vehicle_real_study.py prepare` calls `convert_to_trace`. For `prediction_origin: real_detector_export` it requires:

- vehicle IDs exactly `["1","2","3"]`
- three different `physical_detector_runs` strings
- three different prediction files, one vehicle id per file, re-hashed against the manifest
- one ground-truth file with the same `(take_id, frame_token, roi_id)` keys
- a merged JSONL whose `predictions` match those files row for row
- three checkpoint SHA-256 strings
- ROI frame `cooperscene_global_xy_m`, a finite `center_xy_m`, and a positive `radius_m`
- integer predictions and truth, `0` or `1`, for every vehicle on every ROI

The same checkpoint file may be used for all three vehicles. The three runs still need different run IDs and different output files. Agent `0` must not appear. A cooperative checkpoint must not be substituted.

Because `test.py` mixes every agent in one pkl and does not save boxes, the export has to be done outside `Octopus-main`:

1. Build `cooperscene_infos_test.pkl` with the converter. Confirm the filename; the config's default name is the validate file, `cooperscene_infos_val.pkl`.
2. Split the test infos into three lists by `agent_id` `1`, `2`, and `3`.
3. Run the single-agent model three times, batch size 1, each time with only that agent's infos and a separate output directory. Record the run id, the checkpoint SHA-256, and the sample's `lidar_path`, `agent_id`, and `ego_pose` with every box.
4. Map each predicted center back to world coordinates with the inverse of the converter: rotate the ego-frame point by the ego rotation and add `[x, y, z]` from `lidar_pose`. Do the same for the YAML ground-truth centers, which are already in world coordinates.
5. Apply one score cutoff chosen on train or validate, then frozen. Do not use the 30 test frames to pick it. The visualization default of 0.1 is not that choice.
6. Use a world-XY grid declared before looking at test boxes. The importer example uses radius 7.5 m; any positive radius is accepted, but it has to be fixed in the manifest. A label is 1 when any retained vehicle center lies inside that circle. This is presence, not 3D IoU.
7. Write `vehicle1.jsonl`, `vehicle2.jsonl`, `vehicle3.jsonl`, and `ground_truth.jsonl` with keys `take_id`, `frame_token`, `roi_id`, plus `vehicle_id` and `prediction` or `truth`. Write the merged file with `split`, `predictions`, and `roi.frame = cooperscene_global_xy_m`.
8. From `Octopus-main`, without editing it:

```bash
python scripts/run_three_vehicle_real_study.py prepare \
  --source /path/to/merged.jsonl \
  --manifest /path/to/manifest.json \
  --output /path/to/Negin_validation/P2/cooperscene/mini_run

python scripts/run_three_vehicle_real_study.py evaluate \
  --scenario /path/to/Negin_validation/P2/cooperscene/mini_run/scenario.json \
  --output /path/to/Negin_validation/P2/cooperscene/mini_eval
```

The resulting trace contains only `local:1`, `local:2`, and `local:3`. Energy and latency stay the hypothetical profile in `examples/f0/three_agent_f0.json`. The example error rates 0.06, 0.12, and 0.30 are placeholders. Leave `error_estimator_status` as `unfitted_assumption`, or fit the three rates on the 120 training frames and set `error_fit_split` to `train`.

## Storage and GPU

| Piece | Estimate |
|---|---|
| Mini zip | 2.9 GB, kept intact |
| Extracted mini plus PCD-to-bin conversion | Allow about 10 GB until the scan reports the real size. The zip size does not give the extracted size |
| Single-agent LiDAR checkpoint and config | 115,390,760 bytes plus 17 KB, and the small `_base_` files pulled by `download.py` |
| Docker image | The CUDA 12.1 devel base plus mmcv, mmdet3d, and the compiled ops. Plan on roughly 15–25 GB of image and build cache; that figure is not a measured pull |
| Prediction export | Small. Thirty test frames, three vehicles, and a modest grid are megabytes of JSONL |
| GPU | No published VRAM number. The config's test batch size is 4. Start at batch size 1 and record `nvidia-smi`. The compiled architectures start at compute capability 7.0 |

The mini test split is 30 frames. The scanner warns if train, validate, and test share take IDs. Treat the first successful export as a pipeline check, not a scene-level result.

## Missing components

- No per-vehicle box dump in `tools/test.py`. `format_only` is marked TODO.
- No code in this repository that splits the info file by `agent_id`, inverts `lidar_pose`, or writes the four JSONL files.
- The default evaluation file is the validate split, not the 30-frame test split.
- `huggingface_hub` is required by `tools/download.py` and is absent from `requirements.txt`.
- This checkout has no mini archive, no checkpoint, and no `COOPERSCENE_MINI_RELEASE_SHA256.json`, so `scripts/verify_cooperscene_mini_release.py` cannot run.
- The published benchmark table `samples/three_vehicle_real_published/cooperscene_published_v2v_v2v2.csv` is still missing. It is not an input to this detector run.
- A score cutoff and a world-XY grid have not been frozen on the training frames.
- The machine used for this plan does not have the CUDA 12.1 stack.
