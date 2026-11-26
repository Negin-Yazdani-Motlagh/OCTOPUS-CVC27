# P2 feasibility: real three-vehicle perception

Section 6 lists real three-vehicle predictions, from CooperScene or Mixed Signals, as a later extension. This note inspects the validator and the public releases. No dataset archive was downloaded, no model was trained, and `Octopus-main` was not modified. A roadside sensor and a fused detector are not counted as extra vehicles.

## What is already in this tree

The CooperScene mini validator is CPU software. `octopus_sim/datasets/cooperscene_mini.py` checks a local archive layout. It expects splits `train`, `validate`, and `test`, agents `0`, `1`, `2`, and `3`, and identical timestamps for vehicles `1`, `2`, and `3`. Agent `0` is required for alignment and is not stored as a vehicle. The scanner reads PCD headers and YAML poses. It does not transform boxes, score a detector, or write an OCTOPUS trace. `scripts/check_cooperscene_mini.py` can download `https://data.ucr.edu/datasets/cooperscene/mini.zip`, extract it with path checks, and scan it. That download was not run.

`octopus_sim/datasets/three_vehicle_real.py` accepts only a finished binary ROI export. It requires dataset name `CooperScene`, vehicle IDs exactly `["1","2","3"]`, three distinct detector-run IDs, three separately hashed prediction files, a hashed ground-truth file, and three checkpoint hashes. A merged row that lacks one vehicle, aliases one file as two vehicles, or adds another source is rejected. The written trace has only `local:1`, `local:2`, and `local:3`. It does not invent `edge:*` labels. `scripts/run_three_vehicle_real_study.py` can then score local, majority, and F0, and it labels a synthetic fixture so it cannot be reported as a measurement.

The bundled example is `examples/three_vehicle_real/FIXTURE_NOT_REAL_predictions.jsonl`. Its manifest says `prediction_origin: synthetic_fixture`, and the run IDs begin with `FAKE_`. `examples/cooperscene_mini/` contains no point clouds. A search of this workspace found no `mini.zip`, `.pcd`, or `.pth`.

On 25 Nov 2026 the mini-validator and three-vehicle readiness tests were 23 passed and 1 failed. The failure is the missing published table `samples/three_vehicle_real_published/cooperscene_published_v2v_v2v2.csv`. The passing tests use temporary file layouts, not CooperScene measurements. `scripts/verify_cooperscene_mini_release.py` cannot run: `COOPERSCENE_MINI_RELEASE_SHA256.json` is not in this checkout.

## CooperScene

The project page describes three connected vehicles and one roadside unit, with 59k synchronized LiDAR frames, 53k images, and 344k 3D boxes. The download sizes listed there are about 2.9 GB for the mini set, about 94.3 GB for the full set, and about 90.9 GB for the visualization pack. The mini set is 180 contiguous frames: 120 train, 30 validate, and 30 test. The file layout is `<split>/<take>/<agent>/<timestamp>.{pcd,yaml}`, with a front-camera image on camera-equipped agents. The upstream README numbers four agents. Agent `0` is LiDAR-only. Agents `1`, `2`, and `3` also have a front camera. The cooperative evaluation settings are `V`, `V+V`, `V+2V`, and the same groups with infrastructure (`V+I`, `V+V+I`, `V+2V+I`). `V+2V` is the three-vehicle cooperative case. Its published mAP is one fused result, not three local results.

The model zoo, retrieved through `tools/download.py`, includes single-agent and cooperative checkpoints. The single-agent LiDAR BEVFusion checkpoint is listed at 115 MB, and the single-agent LiDAR-plus-camera checkpoint at 483 MB. The cooperative BEVFusion checkpoints and the six cooperative detectors (V2VNet, V2X-ViT, CoBEVT, V2VAM, ERMVP, CoSDH) are also listed, from about 111 MB to 519 MB. `tools/test.py` reproduces the published mAP. The local smoke note says that command does not write the per-vehicle ROI JSONL this importer requires. No released per-vehicle detection dump is in this tree, and none is referenced as an OCTOPUS input.

Three independent predictions are possible only by executing the single-agent model separately on the point cloud of vehicle 1, vehicle 2, and vehicle 3, and by keeping those three box lists. The same weights may be reused. The executions and output files must stay distinct. The roadside stream, agent `0`, is not a fourth vehicle. A `V+2V` or `V+2V+I` output is one fused prediction and is not one of the three locals.

The mini set can prove that the three vehicle directories and the roadside directory share timestamps. It has 30 test frames, and the scanner warns when train, validate, and test share take IDs. That is a pipeline check, not a three-scene study. Dataset files are CC BY-NC-SA 4.0. The CooperScene code is MIT. Raw files should stay outside this source tree.

## Mixed Signals

Mixed Signals (ICCV 2025, arXiv:2502.14156) records 45.1k point clouds and 240.6k boxes from three connected vehicles plus a roadside unit with two LiDARs. The vehicles are two small electric vehicles and one urban vehicle, all with OS1-128 LiDAR, but the electric-vehicle units are tilted 15 degrees and the urban unit is level. The repository layout names the synchronized streams `003`, `004`, and `laser` for the vehicles, and `top` and `dome` for the two roadside LiDARs. A segment directory stores one point cloud per agent at each shared time index, plus odometry and `V2X_dataset-v0.4-labels.json`.

IEEE DataPort lists the label file (46.65 MB), odometry (3.52 MB), a 148.34 MB miniset, and many point-cloud segment archives. The visible segment files run at least from `PointCloud_mini_1` through `PointCloud_mini_37`, mostly about 2.9 GB each. That release was not downloaded. The paper’s OpenCOOD integration benchmarks Early, Intermediate, and Late fusion, plus Laly fusion, with a PointPillar backbone. Those are fused methods. The repository’s checkpoint instruction is the literal placeholder `Download check points from ???`. No per-vehicle detection archive is linked.

So the three vehicle clouds can be separated from the two roadside LiDARs, and they are stored on a common time index. Independent detector predictions are not in the release. Producing them requires training or obtaining a real checkpoint, running it once per vehicle cloud, and saving three box lists. A late-fusion box list is not a third vehicle, and neither roadside LiDAR is a vehicle.

This OCTOPUS importer cannot take that export unchanged. It requires the dataset string `CooperScene`, vehicle IDs `"1"`, `"2"`, and `"3"`, and the coordinate frame `cooperscene_global_xy_m`. Mixed Signals would need its own contract. There is no Mixed Signals code or data in this workspace.

## Resources required before an evaluation

1. Choose the sensor source. CooperScene mini, about 2.9 GB, is enough to run the existing scanner. A result that is more than a smoke test needs the full CooperScene release, about 94.3 GB, or a Mixed Signals download from IEEE DataPort. Neither was fetched here.
2. Use a CUDA machine for CooperScene. The documented container is PyTorch 2.1.1 and CUDA 12.1, with mmengine and MMDetection3D. Download `bevfusion_single_lidar` or `bevfusion_single_lidarcam`. Do not use `bevfusion_coop_*` or the six cooperative checkpoints as a local vehicle.
3. Run that single-agent model three times, once on each of agents `1`, `2`, and `3`. Save three box files with vehicle ID, split, take, and timestamp. Record three run IDs and the checkpoint SHA-256. Leave agent `0` out of the prediction files.
4. Build a frozen world-XY query grid without looking at the test labels. Project each vehicle’s boxes into binary presence labels, and project the ground truth separately. This box-to-ROI step is not implemented in the current branch.
5. Write the manifest and the four hashed JSONL files required by `DATA_CONTRACT.md`. Fit the three error rates on the training split, or mark them `unfitted_assumption`. Then run `scripts/run_three_vehicle_real_study.py`. Its energy and latency remain the hypothetical profiles until a hardware measurement exists.
6. For Mixed Signals, the same inference plan applies to `003`, `004`, and `laser`, after a real checkpoint replaces the `???` link. `top` and `dome` stay out. The current importer would have to be extended; that change was not made.

Until those exports exist, this repository can validate file layout and can replay a labeled fixture. It cannot report a three-vehicle `R2` or `R3` from CooperScene or Mixed Signals.
