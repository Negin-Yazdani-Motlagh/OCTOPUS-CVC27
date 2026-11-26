# Detector validation

This folder checks whether the single-agent LiDAR checkpoint is actually detecting vehicles before any full inference run. It does not replace the smoke-test notes in `../setup/`. Those files are unchanged.

The test split is not used here. No score cutoff is frozen from this frame.

## 1. Intensity scaling was omitted

Official `tools/dataset_converters/data_converter.py`, function `convert_pcd_to_bin`, reads the PCD `intensity` field with Open3D and divides it by **65535** before writing the float32 `.bin`. The comment in that function says this matches OpenCOOD `pcd_utils.pcd_to_np(isIntensity=True)`.

`../setup/one_frame.sh` reads the same Open3D field and writes it unchanged. There is no division by 65535. On the earlier test frame the saved intensity ran from 3 to 2855, which is the raw field, not the official 0–1 scale.

That omission is confirmed from the two sources. The validation run below shows that it was enough to collapse the detections.

## 2–5. One validation frame

`validate_one_frame.py` does the rest on a single validation frame (agent 1, 2, or 3, the first YAML that contains vehicles):

- Writes the `.bin` with the official `convert_pcd_to_bin`.
- Writes a second `.bin` from the same points with the previous raw intensity.
- Builds ego-frame ground truth with the official `parse_cooperscene_vehicle`.
- Loads `bevfusion_single_lidar.pth` once, permutes 5D sparse-convolution weights only when `permute(1, 2, 3, 4, 0)` matches the model, and records missing keys, unexpected keys, absent checkpoint keys, and any tensor that still does not match.
- Runs both bins through `inference_detector`.
- Saves a bird's-eye plot of predicted boxes against ground truth, plus BEV IoU inside the model's −72 m to 72 m window.

Diagnostic score cuts at 0.05, 0.1, 0.3, and 0.5 are reported so the two inputs can be compared. They are not an operating point.

## Run

Copy this folder to the scratch tree, then run it on the GPU node. From PowerShell, after Yale VPN (Duo: press 1):

```powershell
scp -c aes256-ctr -o MACs=hmac-sha2-512 -o IPQoS=none -r "c:\Users\elyas\OneDrive\Desktop\Negin\Mobihoc_Extention\Mobihoc_Extention\Negin_validation\P2\cooperscene\detector_validation" ei235@bouchet.ycrc.yale.edu:/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/detector_validation
```

On the GPU node:

```bash
sed -i 's/\r$//' /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/detector_validation/run_validation.sh
bash /nfs/roberts/scratch/pi_sjf37/ei235/cs_p2/detector_validation/run_validation.sh
```

The script refuses to start if Python is still bound to the EasyBuild PyTorch libraries. It does not read `data/mini/mini/test` and it does not overwrite `data/one_frame.bin`.

Outputs on the cluster: `report.txt`, `summary.json`, `bev_side_by_side.png`, `bev_official.png`, `bev_previous.png`, the match CSVs, and the saved boxes. The measured lines are copied into `report.txt` in this folder. The PNG files are still only on the cluster.

## Result, 25 November 2026

Job `34721608` on `a1117u29n01`. Frame `validate/1/1/481380.pcd`, agent 1. Checkpoint SHA-256 matches the published file.

| Check | Previous raw intensity | Official intensity / 65535 |
|---|---|---|
| Intensity range | 3 to 2859 | 4.58e-5 to 0.0436 |
| Highest score | 0.125 | 0.889 |
| Best BEV IoU | 0.210 | 0.991 |
| Ground-truth boxes with BEV IoU ≥ 0.5 | 0 of 16 | 15 of 16 |

All 16 ground-truth boxes on this frame sit inside the 72 m window. Weight load: 21 sparse-convolution tensors permuted, 0 still mismatched, 0 missing keys, 0 unexpected keys, 0 checkpoint keys absent from the model.

The published detector is valid once the official preprocessing is used. The earlier smoke-test score of 0.076 was the raw-intensity path on a different frame. One ground-truth box on this validation frame still has BEV IoU below 0.5. No score cutoff is frozen from this single frame, and the test split has not been run.

## Cleanup

Leave `/nfs/roberts/scratch/pi_sjf37/ei235/cs_p2` in place until the study is finished.
