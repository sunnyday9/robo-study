---
title: "Build and run a ROS 2 workspace"
topic: "ROS 2"
order: "061"
description: "Build a Jazzy Python node and trace how a shell finds the installed package."
prerequisites: "Basic Python and a Bash shell on Ubuntu 24.04."
minutes: 40
---

## Make a teammate's shell the acceptance test

You can run a Python file in an editor and see its print statements. Your teammate needs to start the same component by package and executable name from a fresh shell, possibly from a launch file that also starts a recorder. Both of you need to tell which copy of the code ran. That is the problem a workspace solves. On Ubuntu 24.04 with ROS 2 Jazzy, build a small package named `tabletop_tools`, locate its installed prefix, then start `heartbeat` and receive `beat N` in a second terminal. These are separate checkpoints. Save the command and its output at the first one that fails.

A heartbeat lets you build the bench before you have a robot. Pick a payload whose correctness you can see without another library: an increasing integer formatted as text. Pick one setting to vary: the interval between messages. At a period of 0.5 s, the nominal schedule is two messages per second. A listener can join midstream, so seeing `beat 7` first is fine. A heartbeat helps test installation, discovery, and delivery. A simulator observation will later need an actual schema with units, a frame, and a timestamp.

## Follow the package from source to process

<figure class="lesson-figure">
  <a href="/assets/figures/ros-workspace.svg"><img src="/assets/figures/ros-workspace.svg" width="640" height="494" loading="lazy" decoding="async" alt="Edit source, build and install the package, source the overlay in a run shell, then launch the node and observe a heartbeat from another shell."></a>
  <figcaption>Each step proves a different thing. If the package builds but the heartbeat is missing, verify which installed overlay and executable each shell is using.</figcaption>
</figure>

The Jazzy installation at `/opt/ros/jazzy` is the **underlay**. Build your workspace against it. The **overlay** is your workspace's installed output, which takes precedence for packages it supplies when you source it after the underlay. Think of it like adding a local build to several search paths at once. Python's import path is only one of them.

```text
~/robo_ws/src/tabletop_tools/
    package.xml                 -> ROS package identity + dependencies
    resource/tabletop_tools     -> installed ament index marker
    setup.py + setup.cfg         -> install files + place executable wrapper
    tabletop_tools/heartbeat.py -> Python module with main()
                 |
           colcon build
                 v
~/robo_ws/install/tabletop_tools/
    share/ament_index/resource_index/packages/tabletop_tools
    lib/tabletop_tools/heartbeat
    ... installed Python module or symlink ...
                 |
           source local_setup.bash in run shell
                 v
ros2 run tabletop_tools heartbeat -> finds marker -> runs wrapper -> calls main()
```

Read down the diagram to distinguish packaging evidence from program behavior. The marker lets the CLI resolve the package to an installation prefix. The generated wrapper invokes the Python entry point after the CLI finds the executable under `lib/tabletop_tools`. The module can be importable even when either installed artifact is missing. Conversely, a wrapper can exist and crash on its first import if its dependency or interpreter is wrong.

`package.xml` identifies the package and declares dependencies for tools such as rosdep and colcon. `ament_python` selects the Python build type. The scaffold's `setup.py` registers the package marker and manifest as data files and maps `heartbeat` to `tabletop_tools.heartbeat:main` in `console_scripts`. `setup.cfg` puts generated executables where `ros2 run` looks for them. For a plain Python node this is less build machinery than a CMake package. When you later generate custom ROS interfaces or build native code, use an appropriate build type for that package and declare the dependency from the consuming package. This lab can use installed standard interfaces directly.

`colcon` discovers packages and builds them in dependency order. `src/` is your editable input, `build/` has intermediate products, and `log/` helps you investigate build failures. `install/` is the output a running shell or another workspace consumes. This lab uses the default isolated layout, with a prefix for each package. `install/setup.bash` also chains the underlays captured at build time. We use `install/local_setup.bash` after explicitly sourcing Jazzy so the shell's two layers are easy to reproduce. [Jazzy workspace tutorial](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html)

## Lab — publish a synthetic heartbeat

Follow the Jazzy Desktop installation and development tools steps. Use a fresh Ubuntu Bash shell, with any ML virtual environment deactivated, to source the underlay and scaffold the package. The distro's ROS Python extensions are built for its system interpreter. If you add Python environments later, check the interpreter and an actual `import rclpy` before assuming that two shells are equivalent. [Official Jazzy Ubuntu installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) · [Jazzy Python package guide](https://github.com/ros2/ros2_documentation/blob/jazzy/source/How-To-Guides/Using-Python-Packages.rst)

```bash
source /opt/ros/jazzy/setup.bash
echo "$ROS_DISTRO"  # Expected: jazzy
mkdir -p ~/robo_ws/src
cd ~/robo_ws/src
ros2 pkg create --build-type ament_python --license Apache-2.0 \
  --node-name heartbeat tabletop_tools --dependencies rclpy rcl_interfaces std_msgs
```

Replace `~/robo_ws/src/tabletop_tools/tabletop_tools/heartbeat.py` with this runnable node. Keep the generated packaging files. A parameter makes the interval a test input without a source edit. Read and validate it once at startup, then create the timer. The callback owns the sequence and increments it after each publish. `spin` keeps the process available to run ready work, and the cleanup makes it easy to stop, vary one input, and restart.

```python
"""Publish a synthetic sequence for the tabletop labs."""

import math

from rcl_interfaces.msg import ParameterDescriptor
import rclpy
from rclpy.executors import ExternalShutdownException
from std_msgs.msg import String


def main():
    """Run the heartbeat until the ROS context shuts down."""
    rclpy.init()
    node = rclpy.create_node('tabletop_heartbeat')
    try:
        period = node.declare_parameter(
            'period_s', 0.5, ParameterDescriptor(read_only=True)
        ).value
        if not math.isfinite(period) or period <= 0.0:
            raise ValueError('period_s must be finite and positive')

        publisher = node.create_publisher(String, '/tabletop/heartbeat', 10)
        sequence = 0

        def tick():
            nonlocal sequence
            publisher.publish(String(data=f'beat {sequence}'))
            sequence += 1

        node.create_timer(period, tick)
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
```

Build from the workspace root in the underlay-only shell. Initialize rosdep once if it has never been configured on this machine (`sudo rosdep init`). `rosdep` resolves dependency keys to packages for the host. It can help a teammate reproduce what you have installed even if your own build already succeeds. `--packages-select` is enough here because dependencies come from Jazzy. If you add source dependencies to this workspace, `--packages-up-to tabletop_tools` can build the selected package and its workspace dependencies.

```bash
cd ~/robo_ws
colcon list
rosdep update
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon build --symlink-install --packages-select tabletop_tools
```

Save the following as `~/robo_ws/lab-env.bash`. Source it in **each** fresh run or observer terminal with `source ~/robo_ws/lab-env.bash`. Keep a separate build shell with just the Jazzy underlay. If domain 72 is taken, choose a different unused domain in the helper and use it consistently. The lab uses Jazzy Fast DDS and keeps discovery local to one machine.

```bash
source /opt/ros/jazzy/setup.bash || return 1
source "$HOME/robo_ws/install/local_setup.bash" || return 1
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DOMAIN_ID=72 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
unset ROS_STATIC_PEERS ROS_LOCALHOST_ONLY
```

Sourcing applies environment changes to the current shell. Running the helper as `bash lab-env.bash` would apply them in a child process that exits. Keeping settings in a project-specific helper makes two-terminal comparisons repeatable without changing every Bash session on the machine. A build shell left on the underlay also avoids accidentally using artifacts from an earlier build of the same overlay. [Jazzy discovery settings](https://docs.ros.org/en/jazzy/Tutorials/Advanced/Improved-Dynamic-Discovery.html)

In terminal A, locate and run the executable. The expected prefix is `$HOME/robo_ws/install/tabletop_tools` and the expected executable listing is `tabletop_tools heartbeat`.

```bash
ros2 pkg prefix tabletop_tools
ros2 pkg executables tabletop_tools
ros2 run tabletop_tools heartbeat
```

In terminal B, use `timeout 5s ros2 topic echo /tabletop/heartbeat --once`. The expected response is `data: beat N`. Then run `ros2 topic hz /tabletop/heartbeat` for several seconds and stop the rate observer with Ctrl+C. Its reported rate estimates what reached that subscription. Discovery, scheduling, and observer load can affect it.

## Change the interval and predict what moves

Keep the workspace, shells, and observer fixed. Stop A with Ctrl+C and restart with `ros2 run tabletop_tools heartbeat --ros-args -p period_s:=0.25`. In B, confirm `ros2 param get /tabletop_heartbeat period_s`, then repeat the rate probe. Expect the parameter to read 0.25 and the received rate to rise from roughly 2 Hz toward 4 Hz. Those are predictions from the configured periods. Write down your actual rates and observation windows. A reset in the counter is expected when the process restarts.

If the live parameter is right but the rate hardly moves, check which publisher is active with `ros2 topic info -v /tabletop/heartbeat`. More than one publisher ruins the comparison. If there is one and delivery is inconsistent, inspect timing and resource load before changing the timer code. Try setting `period_s` while running and expect rejection: this node sizes the timer at startup and declares the parameter read-only. Supporting live updates would require an explicit validation and timer update path.

## Diagnose the first failing layer

| First failing probe | What to inspect next |
| --- | --- |
| `colcon list` omits the package | Check the directory under `src/`, the manifest, and any ignore marker. |
| `ros2 pkg prefix tabletop_tools` fails or returns the wrong workspace | Compare the result in a fresh underlay-plus-overlay shell. Inspect `AMENT_PREFIX_PATH` and source order. |
| The prefix is right but `ros2 pkg executables tabletop_tools` omits `heartbeat` | Check `console_scripts` and the script location configured in `setup.cfg`. Rebuild packaging changes. |
| The wrapper starts and raises a traceback | Follow the traceback to the import, startup input, or callback that failed. Confirm the module path with `python3 -c 'import tabletop_tools.heartbeat as h; print(h.__file__)'` from outside the source tree. |
| The process stays up but echo times out | Compare shells and inspect discovery and endpoints in [ROS 2 communication](/notes/ros2-communication/). |

For the next iteration, edit the payload prefix temporarily, restart the node, and use echo as a check that the change made it into the process. With `--symlink-install`, changes to an already-linked Python module can be picked up on restart without a build. Changes to entry points, dependencies, or newly installed files still require a rebuild. A copied install costs an extra build for source edits and can be useful when you want to test a fixed artifact. Restore the `beat N` payload and stop the node before moving on.

## Exercises

**1. Diagnose a different shell.** In a fresh terminal, source only Jazzy. From the package directory containing `setup.py`, try importing `tabletop_tools.heartbeat`. Then try `ros2 pkg prefix tabletop_tools`. Predict the result before sourcing the helper.

<details>
<summary>Solution</summary>
<p>With the system ROS dependencies available, Python can import from its working directory. The CLI still needs the installed marker on the ament search path. Source the helper, change to another directory, and verify both the prefix and executable. Those checks establish that the install is visible without relying on the working directory.</p>
</details>

**2. Transfer the workflow to a new executable.** You add `diagnose.py` with a `main()` in the existing Python package. You can import it, but want to run `ros2 run tabletop_tools diagnose`. What changes, and what is the smallest acceptance test?

<details>
<summary>Solution</summary>
<p>Add <code>diagnose = tabletop_tools.diagnose:main</code> to the existing console scripts. Rebuild the package from the underlay-only shell, source the overlay in a fresh run shell, and check that the executable list includes <code>diagnose</code> before starting it. Preserve the heartbeat entry. To check startup behavior independently of DDS, give the new command a small observable output and run it from outside the source directory.</p>
</details>

## Common misconceptions

- **Every terminal inherits my latest build environment.** A shell inherits environment from its parent at startup. Source the intended overlay and discovery settings in each lab shell.
- **A successful build proves the node works.** It establishes that the build finished. Prefix lookup, import, process startup, and message receipt each exercise another boundary.
- **A 0.25 s timer guarantees 4 Hz at the subscriber.** The timer supplies a nominal period. Measure delivery at the observer and investigate deviations with that measurement in mind.

## Summary

Build against a known underlay, locate the installed artifacts from a fresh overlay shell, and then test a visible behavior from another process. The first failed probe tells you which boundary to investigate. Once the baseline works, vary a single startup input and measure the consequence with the same observer.

- [Jazzy Python package scaffolding and entry points](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html)
- [Jazzy parameter descriptor definition](https://raw.githubusercontent.com/ros2/rcl_interfaces/jazzy/rcl_interfaces/msg/ParameterDescriptor.msg)
