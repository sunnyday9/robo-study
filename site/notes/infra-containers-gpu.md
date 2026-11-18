---
title: Reproduce GPU workloads with containers
topic: Infrastructure
order: "41"
description: Pin an OCI image, check GPU access layer by layer, and run a headless simulator with observable inputs and outputs.
prerequisites: Know which host runs each tool from the environment chapter
minutes: 50
---

## Define a repeatable run

Friday's simulation wrote a camera frame. Monday's identical-looking command exits successfully with an empty result directory. Before changing the controller, establish whether the same program, input stage, and hardware path ran. Your target is a launch record that identifies the image, platform, GPU, inputs, and result files, plus a test that fails when its expected output is missing or invalid. Start with a small CPU image to learn the release loop, then apply the same reasoning to GPU execution.

## What an image preserves

An Open Container Initiative (OCI) image packages user-space files and launch metadata. On native Linux, a running container uses the host kernel. The image can pin your ROS packages, Python libraries, and simulator binaries. GPU execution still depends on the host driver, the container runtime's GPU integration, and the device actually assigned to the job.

```text
 Source + locked base + dependencies
                |
              build
                v
         image digest + platform
                |
                v
 Host driver -> container process <- read-only input revision
                |
                +--> result directory + logs (persistent)
                +--> cache (record cold or warm)
```

The arrows into the process explain why two launches of one image can differ. Use a tag to find a release, then save the immutable `repository@sha256:…` reference and platform, such as `linux/amd64`. A tag can move. A multi-platform digest can identify an index whose entries select different manifests. A local image ID identifies the image configuration, while the registry digest identifies a manifest or index. Keep the final digest for reruns, and the Dockerfile, base digest, and dependency lockfiles or package snapshots for rebuilds. A rebuild that resolves packages from a rolling index can change even if the recipe is unchanged. [Docker image digests](https://docs.docker.com/dhi/explore/security-concepts/digests/), [Build practices](https://docs.docker.com/build/building/best-practices/).

| Layer | Record | First diagnosis if it fails |
| --- | --- | --- |
| Host | OS, kernel, GPU model, VRAM, driver | A failing host `nvidia-smi` puts the driver or device first in the investigation. |
| Container runtime | Engine, GPU integration, image digest and platform, assigned devices | If the host sees the GPU and a CUDA test container cannot, inspect the daemon context, runtime configuration, and device request. |
| Application | Simulator build or ML lockfile, graphics or compute backend, launch flags | If both GPU probes pass, verify graphics capability for Isaac or actual tensor placement for PyTorch. |
| External files | Read-only input mounts, writable output directory, asset and dataset revisions | Check paths, file hashes, mount ownership, and free space before interpreting missing output as a simulator fault. |

On native Linux, the NVIDIA Container Toolkit makes the host GPU available to the container. On WSL2, the Windows NVIDIA driver provides CUDA access to Linux workloads. Use the WSL-specific instructions for software installed inside it. Isaac Sim 6.1.0 documents its container deployment for Linux. Use native Ubuntu for that lab, even if a CUDA-only workload works through WSL2. [NVIDIA sample workload](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/sample-workload.html), [CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/), [Isaac Sim container installation](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_container.html).

## Build and test a small OCI image

**Design.** Use the capstone's [validator](/assets/labs/check_trace.py) and [teaching trace](/assets/labs/tabletop-trace.csv). The CSV records simulated observation and command stamps in integer nanoseconds. The validator checks ordering and the skew budget. Packaging both gives CI a synthetic fixture it can exercise without a dataset service or GPU. Put both files and the following `Dockerfile` in a clean build directory. The small Python base exercises packaging independently of the simulator.

```dockerfile
ARG PYTHON_BASE
FROM ${PYTHON_BASE}
WORKDIR /lab
COPY check_trace.py tabletop-trace.csv ./
USER 10001:10001
ENTRYPOINT ["python", "/lab/check_trace.py", "/lab/tabletop-trace.csv"]
```

**Build and run.** In Bash on an already configured x86-64 Linux Docker host, resolve the base once. The first pull fetches the small base image. Keep the resolved reference with the recipe and reuse it for rebuilds.

```bash
docker pull --platform linux/amd64 python:3.12-slim
base=$(docker image inspect python:3.12-slim --format '{{index .RepoDigests 0}}')
printf '%s\n' "$base"
docker build --platform linux/amd64 --build-arg "PYTHON_BASE=$base" \
  -t infra-trace:dev .
docker run --rm --pull=never --network none --read-only infra-trace:dev
```

**Observe and vary.** Expect `OK: 6 rows across 2 episodes` and exit 0. Keep the image, input, and resources and tighten one argument. In the second row of episode `reset-a` the command stamp is 52,000,000 ns and the observation stamp is 50,000,000 ns. The 2,000,000 ns gap exceeds a budget of 1,000,000 ns. Expect a line 3 error and exit 1.

```bash
docker run --rm --pull=never --network none --read-only \
  infra-trace:dev --max-skew-ns 1000000
```

**Debug and iterate.** If neither run starts, check the base resolution, build context, and entrypoint. If both pass, confirm the image contains the intended files and accepts the argument. If only the tightened check fails, restore the baseline and record both statuses. The negative case shows the gate catches excessive delay in this fixture. Copying a tiny fixture into the image makes the smoke test self-contained. Put large or frequently changing stages on read-only mounts to reuse the application image, then treat the mounted files as versioned inputs and check hashes at launch. A mount can also hide files stored at the same path in the image.

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

On a multi-GPU machine, narrow the probe by changing only the device request to `--gpus "device=GPU-…"` with the UUID from the inventory. Expect only the selected device, then return to the original request to confirm the difference. Record device assignment explicitly, since the CUDA ordinal inside a container can differ from the host's numbering.

For an already configured Isaac Sim 6.1.0 container, NVIDIA documents the following command **inside the container**. Save the compatibility report before starting a scene.

```bash
./isaac-sim.compatibility_check.sh --/app/quitAfter=10 --no-window
```

Headless jobs can still render cameras and consume VRAM. Load a small stage, advance a bounded number of simulation steps, and verify that the one expected frame or state file landed in the host output directory. Capture stdout and simulator logs there too. Give caches their own writable mount so you can compare a cold start with a warm one. Check that the container user can write the mount. NVIDIA's `runheadless.sh` example starts livestreaming. For batch jobs, use the release's standalone workflow. [Isaac Sim container launch and mounts](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_container.html), [Isaac Sim standalone Python](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/python_scripting/manual_standalone_python.html).

Suppose your program explicitly renders once every four physics steps, with physics configured for 60 Hz. With a 120-step budget and no initial capture, expect 2 simulated seconds and 30 render calls. These are predictions from the schedule. If you observe 120 steps and zero render calls, investigate stepping and cadence. If there are 30 render calls but zero serialized frames, inspect sensor readiness, serialization errors, and output permissions. Change just the render interval to every two steps, predict 60 calls, and compare the counters, output, and wall time. Separate warmup from steady state and keep cache conditions comparable before attributing a timing difference to the extra renders.

For a bridged run, record the observation before sending the action, and designate one simulation clock. The Isaac Franka smoke test and LeRobot PushT lab have distinct data and action contracts. Joining them requires an explicit adapter.

## Release and recover by digest

Build one candidate from a reviewed source revision, then exercise the packaged program and its negative case. In a release workflow, publish a candidate to an approved registry and resolve its actual manifest or index digest, for example using `docker buildx imagetools inspect` on the candidate reference. Test that registry digest on the intended platform and verify the release runner can resolve the external inputs. Promote the same digest after the relevant CPU and GPU gates pass. A rebuild at promotion time creates a new candidate that needs its own evidence. Save source revision, platform, base digest, artifact revisions, test logs, and the prior working release digest. Roll back by restoring the old digest **and** compatible stage and configuration inputs, then repeat the bounded smoke test. Schedule base updates as deliberate changes with the same checks. [Registry image inspection](https://docs.docker.com/reference/cli/docker/buildx/imagetools/inspect/).

## Exercises

<details>
<summary>Self-check · The CUDA probe passed but an Isaac camera never emits a frame. What does the probe establish?</summary>
<p>The runtime exposes the GPU to the test container. Check the Isaac compatibility report, graphics driver capabilities, RTX and VRAM requirements, and that the scene loaded and advanced far enough to render. Preserve logs before changing the image or driver.</p>
</details>

<details>
<summary>Transfer · The release tag moved overnight. Which evidence lets you repeat yesterday's run?</summary>
<p>Use yesterday's final registry digest and platform along with the exact stage revision and launch configuration. Confirm the host and driver are compatible and inspect the expected output. The Dockerfile and base digest explain how the image was built. A recipe alone may resolve different operating-system packages or wheels during a rebuild.</p>
</details>

## Common misconceptions

- **“Headless means no graphics.”** An offscreen camera can still render and use VRAM.
- **“A green process exit proves the output exists.”** Inspect the mounted output and validate its contents.
- **“The image removes platform differences.”** Record the platform and assigned devices even with a pinned image.

## Summary

Build a small candidate with a known positive and negative case. Pin its content and inputs, then verify host, runtime, and application in that order. Promote the tested digest and retain the inputs needed to replay or roll back.

Use the image digest, stage asset revision, and the GPU probe status for simulated pick-and-place in the [tabletop capstone](/notes/capstone-tabletop/). The run uses virtual sensors and actuators.
