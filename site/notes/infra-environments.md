---
title: Choose a robotics development environment
topic: Infrastructure
order: "40"
description: Match ROS 2, Isaac Sim, and LeRobot to a host and record the versions each one actually uses.
prerequisites: Comfortable with Python and basic shell commands
minutes: 45
---

## Choose for the workload

You inherit a robotics demo that works from its author's terminal. On your laptop the policy imports, the simulator opens on another machine, and the ROS subscriber waits forever. Which part should you reproduce first? Installing every dependency on both machines makes each error harder to isolate. Decide what output each process owes the next one, then build the smallest test that could show where the handoff breaks.

Your target is a host manifest a teammate can use to repeat three scoped checks. A Jazzy shell imports its binary client and, in the local ROS lab, receives one known message. An Isaac Sim 6.1.0 process loads a stage, steps it, and produces the expected state or rendered frame on an eligible host. A LeRobot v0.4.3 environment on Python 3.12 decodes one pinned dataset sample or resets and steps PushT when running the simulator exercise. Record the first missing prerequisite for each blocked check. This gives a developer on a CPU laptop useful work today and a concrete request for a GPU slot tomorrow.

| Host | ROS 2 Jazzy | Isaac Sim 6.1.0 | LeRobot v0.4.3 |
| --- | --- | --- | --- |
| Native Ubuntu 24.04 | Use Jazzy apt packages and system Python. A practical first choice for local replay or a same-host bridge. Check device permissions and drivers separately for hardware. | Workstation for scene editing, Linux container for repeatable headless runs. Both depend on supported graphics hardware and drivers. | Use a dedicated Python 3.12 environment. Resolve the PyTorch build and video backend for this platform. |
| Windows 11 native | NVIDIA documents native Jazzy via Pixi for the Windows Isaac bridge. Follow that release-specific route if bridge integration is the task. | Workstation app on a qualifying RTX GPU. The GUI helps you inspect scene geometry, contacts, and controller behavior. | Tagged metadata omits TorchCodec on Windows. Confirm the PyAV decode path and your policy's wheels with a real sample. |
| Ubuntu 24.04 in WSL2 | Practical for same-environment ROS exercises and local bags. Windows-to-WSL traffic crosses a network boundary. NVIDIA marks its Windows-to-WSL bridge setup deprecated. | A successful CUDA probe in WSL2 checks compute visibility. Use a documented Isaac workstation or Linux container host for this course. | Start with offline datasets or PushT. Treat serial and camera passthrough as separate tests when the workload requires them. |
| Remote native Ubuntu 24.04 | Run the smallest local replay next to the workload and export the results. | Use an eligible RTX host for headless jobs. Provision assets and reserve time for first launch with empty caches. | Run on CPU where the policy permits or schedule a separate compute GPU job. Record where data and outputs live. |

Platform and release references. [Jazzy Ubuntu packages](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/Ubuntu-Install-Debs.rst), [Isaac Sim 6.1.0 requirements](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/requirements.html), [Isaac Sim ROS 2 setup](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_ros.html), [LeRobot v0.4.3 installation](https://huggingface.co/docs/lerobot/v0.4.3/en/installation), [LeRobot v0.4.3 package metadata](https://github.com/huggingface/lerobot/blob/v0.4.3/pyproject.toml).

Start with the hardest constraint. If the deliverable is an Isaac camera frame, a host that can train a small PyTorch model may still lack the required graphics capabilities. NVIDIA's 6.1.0 x86-64 table lists an RTX 4080 and 16 GB of VRAM in its minimum column. As a lower-bound calculation, four 1920 × 1080 cameras with one RGBA8 and one float32 depth buffer each occupy about 66 MB for one set of output buffers. The simulator also needs VRAM for textures, stage data, and intermediate render buffers. Buffer size alone cannot predict total usage. Test a single camera before increasing scene or sensor load. If the deliverable is a dataset transform, a CPU run with one representative decode can answer the immediate question. [Isaac Sim 6.1.0 requirements](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/requirements.html).

## Keep the Python runtimes explicit

The Jazzy `.deb` packages ship native libraries and compiled Python extensions. Importing `rclpy` requires Python to find the package, load an extension built for the interpreter's application binary interface (ABI), and resolve its shared libraries. These are three distinct checks. Use Ubuntu's system interpreter. Source `/opt/ros/jazzy/setup.bash` to expose the apt installation. If developing a ROS package locally, build the workspace against that underlay, then source your workspace overlay in the run shell. Two builds of a package can then be visible, so inspect `rclpy.__file__` and `ros2 pkg prefix <package>` to see what resolved. [ROS 2 Python compatibility guide](https://github.com/ros2/ros2_documentation/blob/jazzy/source/How-To-Guides/Using-Python-Packages.rst).

Use a fresh terminal and a separate Python 3.12 environment for LeRobot. The v0.4.3 package accepts Python 3.10 and newer. If setting up an ML environment, specify `lerobot[pusht]==0.4.3` for the PushT lab, choose your CPU or CUDA wheel source, and resolve a platform-specific lock including transitive dependencies. Keep the lock and its generation command. With a pip-compatible lock containing hashes, a clean environment can install using `python -m pip install --require-hashes -r requirements-linux-x86_64.lock`. That filename describes an input you supply, and Linux CPU and CUDA may need different locks even on the same architecture. Keep wheel hashes and index provenance if two environments must use the same distributions. Finally run the sample decode. The default decoder selection checks whether TorchCodec can be located, so a discovered package can still fail to load a native dependency. [Tagged LeRobot requirements](https://github.com/huggingface/lerobot/blob/v0.4.3/pyproject.toml), [tagged decoder implementation](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/datasets/video_utils.py), [pip hash checking](https://pip.pypa.io/en/stable/topics/secure-installs/).

Use Isaac's release-specific launcher or Python environment for simulator scripts. Here is the process boundary for a bridged simulation and a separate policy lab.

```text
Isaac launcher -> Franka stage -> bridge publishes /clock and state
                                          |
                                          v
                             Jazzy Python -> receives -> bag
                                                          |
                                                          v
                                           optional, explicit adapter
                                           (schema, units, timing)

Python 3.12 venv -> LeRobot v0.4.3 -> pinned data and PushT lab
```

The arrows show where to test the contract. An illustrative observation stamped 100 ms and command stamped 107 ms form a usable pair only if both times are comparable, both belong to the same episode, and the logger records the association. The 7 ms skew fits a 10 ms budget. Specify observation before action and use one simulation clock. An adapter must map fields, feature order, units, and actions before Isaac can supply data to LeRobot. The PushT lab uses its own dataset and environment. A supported in-process integration can avoid serialization overhead. Separate processes may incur copies and need an interface test, but let you resolve dependencies and reproduce failures independently.

## Lab · Inventory one host

**Design and run.** Give each workload a command, expected observable, and status. Start with a ROS import, which requires no simulator. On a preconfigured Ubuntu or Ubuntu WSL2 host, run these Bash commands in a fresh ROS shell. If the setup file is missing, stop the ROS probe and record that prerequisite.

```bash
cat /etc/os-release
uname -m
uname -r
source /opt/ros/jazzy/setup.bash
printf 'ROS distro=%s\n' "$ROS_DISTRO"
dpkg-query -W ros-jazzy-rclpy
/usr/bin/python3 -c "import sys, rclpy; print(sys.executable, rclpy.__file__)"
/usr/bin/python3 -c "from rclpy.utilities import get_rmw_implementation_identifier; print(get_rmw_implementation_identifier())"
```

**Observe.** The expected import line begins with `/usr/bin/python3` and points into the Jazzy installation on a clean apt setup. In a separate, already activated LeRobot shell, run `python --version`, `python -m pip show lerobot torch`, and the following probes. Use the interpreter path in the report even if the version string matches the ROS interpreter.

```bash
python -m pip check
python -c 'import sys, torch; print(sys.executable, torch.__version__, torch.version.cuda, torch.cuda.is_available())'
```

`pip check` checks declared package relationships. A CPU build may show `None False` in the last two fields, which is acceptable for a CPU-only target. On Windows, `wsl --list --verbose` in PowerShell distinguishes WSL1 from WSL2. Record the simulator build from its app or image metadata and the GPU and driver from `nvidia-smi` on an NVIDIA host.

**Vary and explain.** After a successful ROS import, repeat it with `env -u PYTHONPATH /usr/bin/python3 -c "import sys, rclpy; print(sys.executable, rclpy.__file__)"`. This changes one variable for one command. An illustrative result is `ModuleNotFoundError: No module named 'rclpy'`. If it still imports, inspect the path for another installation or a configured search path. A package found but failing with a missing shared object needs a library-path investigation. Restore the baseline by rerunning the original command, then advance from import to the local synthetic topic test in the networking chapter.

**Checkpoint.** Save OS release, kernel, architecture, native versus WSL2, GPU and driver, ROS package version and middleware implementation, simulator build, Python executable paths, ML lock revision, and dataset revision. Attach actual observations beside pass, fail, or skipped. A stale `ROS_DISTRO` inherited from another shell can mislead you. Record the imported module's path alongside it. The inventory is finished when another person can tell which environment to open and which result to expect.

## Exercises

<details>
<summary>Debug · Both shells use Python 3.12, but the ML shell cannot import rclpy. Which test comes first?</summary>
<p>Repeat the import using the system interpreter in a clean, sourced ROS shell. If it passes, compare executable, package path, and native library resolution against the failing process. Keep the ML shell separate and arrange a message or file handoff. If the clean check fails too, inspect the package installation and environment before investigating the ML lock.</p>
</details>

<details>
<summary>Transfer · Plan an afternoon with a CPU laptop and a two-hour remote RTX slot</summary>
<p>Run the local Jazzy import and message check and decode one pinned LeRobot sample on the laptop. Prepare the pinned stage, expected output, and writable result directory before the reservation. On the remote host, inventory the driver, launch the release-specific compatibility check, and run one bounded Franka trial with logs. Use the remaining time to change one scene or sensor setting. Record the local PushT experiment with its own dataset and environment.</p>
</details>

## Common misconceptions

- **“Both environments report Python 3.12, so I can combine them.”** Package resolution, the extension ABI, and shared-library resolution each need evidence.
- **“My shell can see CUDA, so the camera will work.”** Check the graphics stack, scene loading, sensor configuration, and render cadence.
- **“The version in my install instructions identifies the run.”** Record the artifacts the installer resolved, the launcher used, and the actual host.

## Summary

Choose a host from the output the workload must produce. Prove each interpreter, import, and hardware-dependent capability in a small test. Record resolved versions and one known observation, then vary an input you can restore. When you cross a process boundary, test the format and clock contract explicitly.

Bring the manifest to the [tabletop capstone](/notes/capstone-tabletop/) and attach the relevant runtime details to each stage. Next, [package a GPU workload](/notes/infra-containers-gpu/).
