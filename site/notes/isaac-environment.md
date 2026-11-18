---
title: Choose and verify an Isaac Sim environment
topic: Isaac Sim
order: "20"
description: Pin a supported simulator, driver, and ROS 2 combination, then isolate startup, rendering, and asset failures.
prerequisites: Comfort running Python and shell commands
minutes: 35
---

## What a working environment proves

Imagine borrowing a GPU machine to collect wrist-camera demonstrations. Your training script sees CUDA and the simulator opens, but the robot reference is empty and the camera stream never arrives. How much of the stack has actually passed? If you answer that question before installing everything, you can diagnose the first failing boundary instead of changing the driver, Python environment, and ROS settings together.

Build an acceptance record for one machine. A useful first result is a visible rigid cube that falls and comes to rest on a plane, followed by a successful update in a separate, headless Python process. These observations cover different execution paths. Later chapters extend the record with a referenced Franka asset, a functioning controller, and a stamped ROS camera stream. The checkpoints reveal what a machine can support before you spend time designing the full experiment.

This track uses the **Isaac Sim 6.1.0 standalone binary on x86-64**. The reference path for the full track is native **Ubuntu 24.04 with ROS 2 Jazzy** using standard interfaces. Windows 11 can run the workstation build. Its bridge has a separate platform-specific setup, so use the Linux reference path if you want to follow the ROS lab verbatim. NVIDIA supports the Isaac Sim container on Linux. On a Mac or a machine without a supported RTX GPU, use a supported remote simulation host or work through the capstone's replay stage locally. [NVIDIA requirements](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/requirements.html) · [ROS 2 platform matrix](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_ros.html)

| Decision | What to verify before installing |
| --- | --- |
| Simulator | Match the download, documentation, examples, and assets to the same release. The installation's `VERSION` file identifies the build. |
| Host and driver | Compare the OS, GPU, VRAM, RAM, and storage against the release matrix. NVIDIA lists an RTX 4080 with 16 GB VRAM as the x86-64 minimum specification and records the drivers it tested. Check the driver notes for your exact GPU. |
| ROS 2 | Check the host OS, ROS distribution, and middleware together. Add the bridge only after the base simulation works. |
| Execution mode | Use the desktop viewport for inspecting scenes. Use standalone Python for scripted runs with fixed stopping conditions. Headless removes the window and can still render cameras on the GPU. |

## Follow the component boundaries

```text
Host OS and driver
  |  GPU enumeration is the first probe (nvidia-smi)
  v
Kit process and enabled extensions
  |-- USD composition loads scene descriptions and asset references
  |-- PhysX reads physics schemas and advances rigid-body state
  |-- RTX renderer turns scene state into pixels and sensor products
  `-- ROS 2 bridge serializes selected state or sensor data
        |
        v
      Separate Jazzy process receives messages over middleware
```

Read this as a dependency diagram. Asset resolution, physics, and rendering are different functions inside the running application. A cube made with a built-in shape can exercise the solver and viewport with zero robot downloads. If that probe passes and a referenced robot is missing, investigation moves to asset composition. A picture in the viewport verifies one render path. A bridge subscriber still needs a configured render product, an enabled publisher, and compatible middleware settings. Use the probe nearest the failure to decide where to look next. [NVIDIA reference architecture](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/introduction/reference_architecture.html)

The workstation launcher starts a Kit application that manages its own update loop. In standalone Python you first create `SimulationApp`, then import modules that need Kit and call updates from your script. Treat the wrapper as part of the runtime: it sets paths for bundled Python modules, extensions and native libraries. An ordinary machine-learning virtualenv can have the same Python major and minor version and still lack these paths or expose a conflicting library. Keep the simulator process and external Jazzy tools in their prescribed environments. A ROS message crossing a process boundary has a wire contract. Importing a native Python module into Kit has an additional binary compatibility contract. [NVIDIA standalone Python](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/python_scripting/manual_standalone_python.html) · [NVIDIA ROS setup](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_ros.html)

Choose how you work based on what you need to observe. The viewport is efficient when you need to inspect transforms and colliders interactively. Standalone scripting makes configuration and exit status easier to reproduce. A supported Linux container can package user-space dependencies for a repeatable deployment, but the host driver and GPU exposure still participate. A remote GPU host moves expensive work off your laptop at the cost of another copy boundary for assets and logs. The capstone replay is useful on a CPU for exercising the reader and data contract while GPU access is being arranged. [NVIDIA container installation](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_container.html) · [Tabletop capstone](/notes/capstone-tabletop/)

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

3. Allow time for first-run shader compilation. Create a new stage, then add a **Ground Plane** from **Create → Physics**, a **Distant Light** from **Create → Lights**, and a **Cube** from **Create → Shape**. Move the cube above the plane. With the cube selected, record its size and initial vertical translation. In the Property panel use **Add → Physics → Rigid Body with Colliders Preset**. Press **Play** and check for a visible cube that falls and rests on the plane. Observe its vertical pose at rest. This adds a viewport and physics check to the Kit startup check. [NVIDIA basic usage tutorial](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/introduction/quickstart_isaacsim.html)
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

**Checkpoint.** Keep the build, GPU and driver, Test Kit result, desktop observation, and headless exit status together. In Bash, capture `$?` immediately after the command. In PowerShell inspect `$LASTEXITCODE`. The headless message confirms an app update and the exit status checks the process finished successfully. Use the [scene lab](/notes/isaac-scene/) to verify that referenced robot assets resolve and the [bridge lab](/notes/isaac-ros-bridge/) to verify sensor output. [NVIDIA standalone Python](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/python_scripting/manual_standalone_python.html)

## Predict, vary, and explain the cube test

Pick a height you can reason about. For an illustrative stage with meters as its units, Z up, and an unscaled 0.20 m cube centered at 1.10 m, the cube's bottom begins 1.00 m above the plane. In ideal free fall with gravity 9.81 m/s² it takes √(2 × 1.00 / 9.81) ≈ 0.45 simulated seconds to reach the plane. Its center should rest near 0.10 m if it lands flat. These are predictions. The solver advances in discrete steps, contacts have tolerances, and elapsed wall time includes graphics and scheduling. Use height and a stable final pose as acceptance criteria before adding a precise timing assertion.

Save a copy of the simple stage. With playback stopped, disable the cube's collider using its collision property and leave its rigid body enabled. Reset it to the same pose and replay. Predict that gravity will still move it, but the plane will no longer halt it. If it disappears, follow its Z translation instead of assuming it failed to render. Restore the collider, restart from the same pose, and verify the cube rests again. This gives you a known example of a visible mesh, a moving rigid body, and an absent contact in the same run. When a more complex object later falls through a table, you already know which properties to inspect.

## Debug from the first failing line

| Illustrative record | Next discriminating check |
| --- | --- |
| Device enumeration fails | Check the GPU and driver on the host first. If the host passes but a Linux container fails, inspect how the GPU was exposed to that container. |
| Device is listed, Test Kit fails | Compare the exact device and driver against the matrix. Read the first renderer or extension initialization error and save the startup log. |
| Test Kit passes, desktop launch stalls | Let first-run shaders compile and inspect the log for progress. Compare with a second launch before drawing a throughput conclusion. |
| Cube is visible and stationary during Play | Inspect physics enablement, the cube's dynamic body setting, and playing state. A light controls shading and has no effect on gravity. |
| Headless wrapper exits successfully, referenced robot is empty | Inspect the USD reference and asset root configuration. Check that the asset can be resolved from inside the simulator host or container. |

Keep one record per attempt with the launch command, elapsed startup time, first diagnostic error, and observed result. Preserve the failing record before changing a setting. For an asset access problem, for example, keep the known-good primitive stage and rerun it after correcting the asset root. Then open the referenced example again. A repaired reference and a still-working primitive isolate the improvement to the boundary you changed. [NVIDIA asset setup](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/accessing_assets.html)

## Exercises and solutions

A remote Linux VM sees its NVIDIA A100 in `nvidia-smi`. Is that sufficient to choose it for the headless camera lab?

<details>
<summary>Check your answer</summary>
<p>The 6.1.0 requirements exclude GPUs without RT cores, including the A100. Select a supported GPU for the camera lab. Confirm GPU visibility, Kit startup, and actual image capture as separate probes. You can run the capstone replay on the CPU while waiting for that host.</p>
</details>

A colleague's desktop app passes the cube test. Their headless script fails before printing anything with an import error, and the command in their log is `python smoke_isaac.py` from a training virtualenv. Which two checks would you run first?

<details>
<summary>Check your answer</summary>
<p>Run the same file with the installation's Python wrapper and inspect the first exception. If it now reaches Kit but fails on an extension import, inspect import order. Put initialization before imports that require the running app. If the app starts, retain the original and corrected launch commands as evidence. Changing the GPU driver would leave the import-path hypothesis untested.</p>
</details>

## Common misconceptions

- **A single successful startup certifies the workstation.** A startup smoke test covers initialization. Throughput, asset access, and camera capture require work from additional components.
- **A container owns every dependency.** The image carries user-space components, while the host provides the driver and access to the GPU.
- **Headless makes the test CPU-only.** Headless controls the window. A workload that requests RTX-rendered images still exercises the GPU renderer.

## Summary

Pin the release and host combination, then design probes whose failure has a small set of explanations. The primitive scene isolates physics and rendering from asset access. The headless wrapper isolates the scripted launch path. Carry the recorded baseline into the Franka lab so a new scene introduces one new class of problems at a time.
