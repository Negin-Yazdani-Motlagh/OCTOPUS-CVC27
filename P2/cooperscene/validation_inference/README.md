# Validation inference

Runs the published single-agent LiDAR checkpoint on the CooperScene mini validation split, once for vehicle 1, once for vehicle 2, and once for vehicle 3. Intensity is converted by the official `convert_pcd_to_bin`, which divides by 65535.

The test split is not read. Agent 0 is not read. The model is not trained. `Octopus-main` is not modified. The earlier smoke-test and one-frame validation files are left in place.

Matching is one-to-one in the ego lidar frame. A pair counts only when BEV IoU reaches 0.50 or 0.70. Score cutoffs are the predefined values 0.05, 0.1, 0.3, and 0.5. Inference time is the detector forward pass after the point cloud is already a `.bin`. The first frame of each vehicle is a warmup; the report also gives the mean without it. Peak GPU memory is the PyTorch allocator peak.

The score recommendation uses pooled F1 at IoU 0.50. If two cutoffs are within 0.01 F1, the higher cutoff is kept. The world grid uses radius 7.5 m, the radius already named for this study, on a 15 m lattice that covers validation ground truth. It is not fit on the test split.

## Run

On the GPU node, after this folder has been copied to scratch:

```bash
sed -i 's/\r$//' /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/validation_inference/run_validation_inference.sh
bash /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/validation_inference/run_validation_inference.sh
```

Outputs in that directory: `vehicle_1.jsonl`, `vehicle_2.jsonl`, `vehicle_3.jsonl`, `metrics.csv`, `summary.json`, and `report.txt`. Each JSONL row has the timestamp, vehicle id, sensor pose, ego and world boxes, scores, inference seconds, and the match counts.

## Result

The run on 25 November 2026 finished all 30 validation frames for vehicles 1, 2, and 3, with no failures. The measured table is in `report.txt`. The cutoff and grid recommendation is in `RECOMMENDATION.md`.

Use score **0.1**. On the pooled validation set at one-to-one BEV IoU 0.50 that cutoff has precision 0.943, recall 0.980, and F1 0.962. The world grid is 144 circles of radius 7.5 m on a 15 m lattice with origin (−75 m, −105 m), in frame `cooperscene_global_xy_m`. A circle can contain more than one vehicle, so the label is presence.
