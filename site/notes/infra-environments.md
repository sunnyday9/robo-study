---
title: Choose a robotics development environment
topic: Infrastructure
order: "40"
description: Match ROS 2, Isaac Sim, and LeRobot to a host and record the versions each one actually uses.
prerequisites: Comfortable with Python and basic shell commands
minutes: 25
---

## Choose for the workload

ROS 2 moves typed messages between processes. Isaac Sim runs physics and renders virtual sensors. LeRobot loads robot datasets and trains or evaluates policies. A Python environment can isolate Python packages, but it cannot supply an operating system's device access or a compatible graphics driver. Choose the host for the hardest requirement, then give each tool its own runtime.

The course uses Ubuntu 24.04, ROS 2 Jazzy, Isaac Sim 6.1.0, and LeRobot v0.4.3 with Python 3.12. These are lab references, not a claim that each is the latest release or that the three tools share a process or environment. Verify the exact GPU, renderer, policy, and bridge before planning a combined run.

| Tool | Windows 11 and WSL2 | Native Ubuntu 24.04 |
| --- | --- | --- |
| ROS 2 Jazzy | Ubuntu 24.04 in WSL2 is convenient for local ROS exercises and bag replay. A Windows app and WSL2 ROS nodes cross a network boundary. For a native Windows Isaac bridge, NVIDIA documents a Pixi route and marks its WSL2 bridge route deprecated. | Use the Jazzy apt packages. This is the simplest baseline when discovery, USB devices, or a Linux simulator must share the machine. |
| Isaac Sim 6.1.0 | Run the supported native Windows workstation app on a qualifying RTX GPU. Successful CUDA access in WSL2 establishes a compute capability only. | Use the workstation app for interactive scene work, or NVIDIA's Linux container for headless jobs. Check the release's GPU, VRAM, and driver requirements. |
| LeRobot v0.4.3 | Start with offline datasets inside WSL2 for parity with Linux examples. For native Windows, v0.4.3 omits TorchCodec from its dependencies. Check the PyAV decode path and your policy's wheels separately. Treat serial and camera access as separate hardware checks. | Use a dedicated Python 3.12 environment. Pick the PyTorch build and decoder for your workflow, and reserve device access for a separate hardware session. |

Platform and release references. [Jazzy Ubuntu packages](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/Ubuntu-Install-Debs.rst), [Isaac Sim 6.1.0 requirements](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/requirements.html), [Isaac Sim ROS 2 setup](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_ros.html), [LeRobot v0.4.3 installation](https://huggingface.co/docs/lerobot/v0.4.3/en/installation), [LeRobot v0.4.3 package metadata](https://github.com/huggingface/lerobot/blob/v0.4.3/pyproject.toml).

## Keep the Python runtimes explicit

The Jazzy `.deb` packages on Ubuntu include native libraries and compiled Python modules such as `rclpy`. The interpreter must match the build ABI. Use Ubuntu's system interpreter for the apt-installed ROS tools. Sourcing `/opt/ros/jazzy/setup.bash` in a ROS terminal makes the installation visible to that shell. A sourced ROS workspace overlay can also change which build a command finds.

Use a fresh terminal and a separate Python 3.12 environment for LeRobot v0.4.3. The tagged package accepts Python 3.10 and newer, and this course uses 3.12. Pin transitive dependencies and record the PyTorch build and video backend you resolved. Use Isaac Sim's release-specific launcher or documented Python environment for simulator scripts. If the tools need to exchange data, use a documented message or file format and test the schema at that boundary. [ROS 2 Python compatibility guide](https://github.com/ros2/ros2_documentation/blob/jazzy/source/How-To-Guides/Using-Python-Packages.rst).

## Lab · Inventory one host

On a preconfigured Ubuntu or Ubuntu WSL2 host, run these Bash commands in a fresh ROS shell. They inspect the runtime and do not install packages.

```bash
cat /etc/os-release
uname -m
uname -r
source /opt/ros/jazzy/setup.bash
printf 'ROS distro=%s\n' "$ROS_DISTRO"
dpkg-query -W ros-jazzy-ros-base
/usr/bin/python3 -c "import sys, rclpy; print(sys.executable, rclpy.__file__)"
```

In a separate, already activated LeRobot shell, run `python --version` and `python -m pip show lerobot torch`. On Windows, `wsl --list --verbose` in PowerShell distinguishes WSL1 from WSL2. Record the simulator build from its app or image metadata and, for an NVIDIA host, the GPU and driver from `nvidia-smi`.

**Checkpoint.** Write a one-page host manifest with OS release, kernel, CPU architecture, native versus WSL2, GPU and driver, ROS package version and middleware implementation, simulator build, Python executable paths, and the ML lockfile revision. Use “unavailable” for missing components. If `rclpy` fails in the system interpreter, check that Jazzy is installed and sourced. If it fails only inside the ML environment, compare interpreter paths and native dependencies before reinstalling anything.

<details>
<summary>Self-check · Why can a working Python 3.12 ML shell still fail to import rclpy?</summary>
<p>The interpreter version is one part of the binary contract. The ROS setup also supplies search paths for ROS packages and their shared libraries, and a separate environment can supply conflicting native libraries. Compare with a fresh ROS shell using the system interpreter.</p>
</details>

Bring the manifest to the [tabletop capstone](/notes/capstone-tabletop/) and attach the relevant runtime details to each stage. Next, [package a GPU workload](/notes/infra-containers-gpu/).
