---
title: Choose and verify an Isaac Sim environment
topic: Isaac Sim
order: "20"
description: Pin a supported simulator, driver, and ROS 2 combination, then isolate startup, rendering, and asset failures.
prerequisites: Comfort running Python and shell commands
minutes: 35
---

## Choose the stack as a unit

Isaac Sim runs robot physics, renders virtual sensors, and can exchange messages with ROS 2. Each layer has different dependencies. A working Python environment or CUDA workload tells you little about whether the simulator can start its Omniverse Kit runtime and initialize an RTX renderer.

This track uses the **Isaac Sim 6.1.0 standalone binary on x86-64**. The reference path for the full track is native **Ubuntu 24.04 with ROS 2 Jazzy** using standard interfaces. Windows 11 can run the workstation build. Its bridge has a separate platform-specific setup, so use the Linux reference path if you want to follow the ROS lab verbatim. NVIDIA supports the Isaac Sim container on Linux. On a Mac or a machine without a supported RTX GPU, use a supported remote simulation host or work through the capstone's replay stage locally. [NVIDIA requirements](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/requirements.html) · [ROS 2 platform matrix](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_ros.html)

| Decision | What to verify before installing |
| --- | --- |
| Simulator | Match the download, documentation, examples, and assets to the same release. The installation's `VERSION` file identifies the build. |
| Host and driver | Compare the OS, GPU, VRAM, RAM, and storage against the release matrix. NVIDIA lists an RTX 4080 with 16 GB VRAM as the x86-64 minimum specification and records the drivers it tested. Check the driver notes for your exact GPU. |
| ROS 2 | Check the host OS, ROS distribution, and middleware together. Add the bridge only after the base simulation works. |
| Execution mode | Use the desktop viewport for inspecting scenes. Use standalone Python for scripted runs with fixed stopping conditions. Headless removes the window and can still render cameras on the GPU. |

## Lab · verify one layer at a time

1. Download the **6.1.0** workstation archive for your OS. Follow NVIDIA's extraction and `post_install` steps. Open a terminal in the extracted installation directory. [Release downloads](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/download.html) · [Workstation setup](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_workstation.html)
2. Run the commands below for your platform. In the Compatibility Checker, run **Test Kit** and record its result. Close the checker before opening the full app.

   ```bash
   # Linux, from the extracted installation
   cat VERSION
   nvidia-smi
   ./isaac-sim.compatibility_check.sh
   ./isaac-sim.sh
   ```

   ```powershell
   # Windows PowerShell, from the extracted installation
   Get-Content VERSION
   nvidia-smi
   .\isaac-sim.compatibility_check.bat
   .\isaac-sim.bat
   ```

3. Allow time for first-run shader compilation. Create a new stage, then add a **Ground Plane** from **Create → Physics**, a **Distant Light** from **Create → Lights**, and a **Cube** from **Create → Shape**. Move the cube above the plane. Select the cube and use the Property panel's **Add → Physics → Rigid Body with Colliders Preset**. Press **Play** and check for a visible cube that falls and rests on the plane. This adds a check of the viewport and physics to the Kit startup check. [NVIDIA basic usage tutorial](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/introduction/quickstart_isaacsim.html)
4. Close the app. Save the runnable program below as `smoke_isaac.py` in the extracted installation. Run `./python.sh smoke_isaac.py` on Linux or `.\python.bat smoke_isaac.py` in Windows PowerShell. The supplied wrapper sets up the simulator's runtime. Initialize `SimulationApp` before importing Kit extensions.

   ```python
   from isaacsim import SimulationApp

   app = SimulationApp({"headless": True})
   try:
       app.update()
       print("Headless app update completed")
   finally:
       app.close()
   ```

**Checkpoint.** Keep the build, GPU and driver, Test Kit result, desktop observation, and headless exit status together. The headless message confirms an app update. Use the [scene lab](/notes/isaac-scene/) to verify that referenced robot assets resolve and the [bridge lab](/notes/isaac-ros-bridge/) to verify sensor output. [NVIDIA standalone Python](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/python_scripting/manual_standalone_python.html)

**Diagnostics.** If `nvidia-smi` fails, check driver installation or GPU visibility in the host or container. If it succeeds but Test Kit fails, inspect the Kit log for renderer initialization errors and compare the GPU and driver with the matrix. If the cube test works but a packaged robot is missing, check the asset root and any failed reference URLs. [NVIDIA asset setup](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/accessing_assets.html)

## Self-check

A remote Linux VM sees its NVIDIA A100 in `nvidia-smi`. Is that sufficient to choose it for the headless camera lab?

<details>
<summary>Check your answer</summary>
<p>No. The 6.1.0 requirements exclude GPUs without RT cores, including the A100. A headless camera still needs a renderer. Check for a supported GPU, then confirm startup and capture separately.</p>
</details>
