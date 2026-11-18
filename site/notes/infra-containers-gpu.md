---
title: Reproduce GPU workloads with containers
topic: Infrastructure
order: "41"
description: Pin an OCI image, check GPU access layer by layer, and run a headless simulator with observable inputs and outputs.
prerequisites: Know which host runs each tool from the environment chapter
minutes: 30
---

## What an image preserves

An Open Container Initiative (OCI) image packages user-space files and launch metadata. On native Linux, a running container uses the host kernel. The image can pin your ROS packages, Python libraries, and simulator binaries. GPU execution still depends on the host driver, the container runtime's GPU integration, and the device actually assigned to the job.

Use a version tag to find a release, then save the resolved `repository@sha256:…` reference and platform, such as `linux/amd64`. A tag can move. A multi-platform digest can point to an index whose platform entries resolve to distinct images. Pin the final image for repeat runs. For rebuilds, also retain the Dockerfile, base image digest, and dependency lockfiles or package snapshots. [Docker image digests](https://docs.docker.com/dhi/explore/security-concepts/digests/).

| Layer | Record | First diagnosis if it fails |
| --- | --- | --- |
| Host | OS, kernel, GPU model, VRAM, driver | A failing host `nvidia-smi` puts the driver or device first in the investigation. |
| Container runtime | Engine, GPU integration, image digest and platform, assigned devices | If the host sees the GPU and a CUDA test container cannot, inspect the daemon context, runtime configuration, and device request. |
| Application | Simulator build or ML lockfile, graphics or compute backend, launch flags | If both GPU probes pass, verify graphics capability for Isaac or actual tensor placement for PyTorch. |
| External files | Read-only input mounts, writable output directory, asset and dataset revisions | Check paths, file hashes, mount ownership, and free space before interpreting missing output as a simulator fault. |

On native Linux, the NVIDIA Container Toolkit makes the host GPU available to the container. On WSL2, the Windows NVIDIA driver provides CUDA access to Linux workloads. Use the WSL-specific instructions for software installed inside it. Isaac Sim 6.1.0 documents its container deployment for Linux. Use native Ubuntu for that lab, even if a CUDA-only workload works through WSL2. [NVIDIA sample workload](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/sample-workload.html), [CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/), [Isaac Sim container installation](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_container.html).

## Lab · Prove one layer at a time

Run these Bash commands on an already configured native Ubuntu NVIDIA machine using its local Docker daemon and the preloaded validation image. The transient container runs only a GPU inventory command. The pull policy requires a local image and the container has networking disabled. [Docker run options](https://docs.docker.com/reference/cli/docker/container/run/).

```bash
nvidia-smi
docker image inspect nvcr.io/nvidia/cuda:12.8.0-base-ubuntu24.04 \
  --format '{{.Os}}/{{.Architecture}} {{json .RepoDigests}}'
docker run --rm --pull=never --network none --runtime=nvidia --gpus all \
  nvcr.io/nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi
```

**Checkpoint.** Compare the GPU UUID and driver in the two inventories. A missing image is a provisioning gap. A GPU listed inside the container confirms visibility but leaves rendering and application execution untested. If you lack this host, use the table to write down the expected observations and mark the probe skipped.

For an already configured Isaac Sim 6.1.0 container, NVIDIA documents the following command **inside the container**. Save the compatibility report before starting a scene.

```bash
./isaac-sim.compatibility_check.sh --/app/quitAfter=10 --no-window
```

Headless jobs can still render cameras and consume VRAM. Load a small stage, advance a bounded number of simulation steps, and verify that the one expected frame or state file landed in the host output directory. Capture stdout and simulator logs there too. Give caches their own writable mount so you can compare a cold start with a warm one. Check that the container user can write the mount. NVIDIA's `runheadless.sh` example starts livestreaming. For batch jobs, use the release's standalone workflow. [Isaac Sim container launch and mounts](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_container.html), [Isaac Sim standalone Python](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/python_scripting/manual_standalone_python.html).

<details>
<summary>Self-check · The CUDA probe passed but an Isaac camera never emits a frame. What does the probe establish?</summary>
<p>The runtime exposes the GPU to the test container. Check the Isaac compatibility report, graphics driver capabilities, RTX and VRAM requirements, and that the scene loaded and advanced far enough to render. Preserve logs before changing the image or driver.</p>
</details>

Use the image digest, stage asset revision, and the GPU probe status for simulated pick-and-place in the [tabletop capstone](/notes/capstone-tabletop/). The run uses virtual sensors and actuators.
