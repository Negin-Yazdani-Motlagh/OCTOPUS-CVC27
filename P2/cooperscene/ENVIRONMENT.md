# CooperScene single-agent LiDAR BEVFusion: this machine

Checked on this Mac without installing packages, downloading the dataset, or changing `Octopus-main`. The official detector cannot run here. It needs a remote Linux machine with an NVIDIA GPU and CUDA 12.1.

## What this computer is

| Item | Observed |
|---|---|
| Machine | MacBook Air, Apple M4 |
| OS | macOS 26.6.2, Darwin 25.6.0, arm64 |
| CPU | 10 cores (4 performance, 6 efficiency) |
| GPU | Apple M4, 8 cores, Metal. Built in |
| Memory | 16 GB unified |
| Disk | 228 GB volume, 69 GB free. The project tree is 328 MB |
| CUDA | `nvidia-smi` and `nvcc` are not installed |
| Docker | `docker` is not installed |
| Python | `/usr/bin/python3` is 3.9.6. The validation virtualenv is Python 3.13.2 |
| Detector packages | The virtualenv has NumPy 2.5.5. It does not have PyTorch, mmcv, mmengine, mmdet, mmdet3d, spconv, shapely, Open3D, einops, or `huggingface_hub` |

A live memory snapshot showed the compressor in use and existing swap traffic. That does not change the hardware limit: 16 GB is shared by the CPU and the Apple GPU.

## What the checkpoint requires

From the CooperScene Dockerfile, `requirements.txt`, and README, as recorded in `PLAN.md`:

- Linux
- Python 3.10
- PyTorch 2.1.1 with CUDA 12.1
- `mmengine>=0.10`, `mmcv>=2.0,<2.2`, `mmdet>=3.2,<3.4`, `mmdet3d>=1.4,<1.5`
- `numpy<1.25`
- `spconv-cu120`, which is a CUDA 12 wheel
- BEVFusion CUDA ops compiled for compute capability 7.0, 7.5, 8.0, 8.6, 8.9, and 9.0
- an NVIDIA GPU. The published config tests at batch size 4 and does not state a VRAM number

## Compatibility

| Requirement | This Mac |
|---|---|
| Linux | macOS |
| NVIDIA GPU, compute capability 7.0 or newer | Apple GPU only. No CUDA device |
| CUDA 12.1 and `spconv-cu120` | No CUDA toolkit and no NVIDIA driver |
| Python 3.10 | 3.9.6 and 3.13.2. Neither is the tested interpreter |
| `numpy<1.25` | The validation environment has NumPy 2.5.5 |
| PyTorch 2.1.1, mmcv, mmdet3d | Not installed. Those wheels are built for Linux CUDA, not Metal |
| About 2.9 GB of mini data plus a 115 MB checkpoint | 69 GB is free, so the files would fit |
| Docker image, roughly 15–25 GB | Docker is not installed, and a container would still have no NVIDIA GPU |

Disk space is the only requirement this machine can meet. The model’s voxel and BEV-pool kernels are CUDA code. Metal cannot run that stack, and installing PyTorch for macOS would not make `tools/test.py` the official CooperScene run.

## Decision

Run the pretrained single-agent LiDAR BEVFusion model on a remote Linux GPU host. This Mac can keep the plan, the later JSONL exports, and the OCTOPUS evaluation. It should not be the machine that executes the detector.

The remote host needs:

- Linux, Python 3.10, and the Docker image `pytorch/pytorch:2.1.1-cuda12.1-cudnn8-devel`, or the same pins installed with `mim`
- an NVIDIA GPU whose compute capability is in `7.0;7.5;8.0;8.6;8.9;9.0`
- enough free disk for the 2.9 GB mini zip, its extracted clouds, the 115,390,760-byte checkpoint, and the image build
- a first inference at batch size 1, with GPU memory recorded there, because CooperScene does not publish a VRAM figure
