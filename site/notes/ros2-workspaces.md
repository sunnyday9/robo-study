---
title: "Build and run a ROS 2 workspace"
topic: "ROS 2"
order: "10"
description: "Build a Jazzy Python node and trace how a shell finds the installed package."
prerequisites: "Basic Python and a Bash shell on Ubuntu 24.04."
minutes: 40
---

## Follow the package from source to process

ROS 2 Jazzy publishes binary packages for Ubuntu 24.04 (Noble). The system installation is your **underlay**. Your own packages live in an **overlay** built against that underlay. Think of the overlay as an installation prefix that takes precedence over the underlay in a sourced shell. A successful build and a successful package lookup are separate checkpoints.

| Piece | Question it answers |
| --- | --- |
| `src/` and `package.xml` | Where is the source, and which ROS dependencies does it declare? |
| `ament_python`, `setup.py`, `setup.cfg` | How does setuptools install the module, its ROS package marker, and the executable wrapper? |
| `colcon build` | In what order should workspace packages build, and where should their artifacts go? |
| `install/local_setup.bash` | How does this shell add the built overlay to its package and executable search paths? |

`src/` holds the editable files. `build/` and `log/` hold intermediate products and diagnostics. `install/` is the tree a downstream workspace or a running shell consumes. `install/setup.bash` also sources the underlays captured at build time. Here you source the underlay explicitly so the order is visible. [Jazzy workspace tutorial](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html)

## Lab — publish a synthetic heartbeat

Follow the Jazzy Desktop installation and development tools steps. Use a fresh Ubuntu Bash shell to source the underlay and scaffold the package. [Official Jazzy Ubuntu installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)

```bash
source /opt/ros/jazzy/setup.bash
echo "$ROS_DISTRO"  # Expected: jazzy
mkdir -p ~/robo_ws/src
cd ~/robo_ws/src
ros2 pkg create --build-type ament_python --license Apache-2.0 \
  --node-name heartbeat tabletop_tools --dependencies rclpy rcl_interfaces std_msgs
```

Replace `~/robo_ws/src/tabletop_tools/tabletop_tools/heartbeat.py` with this runnable node. Keep the generated packaging files. The generated `heartbeat` console script calls `tabletop_tools.heartbeat:main`. The timer registers work, and spinning the node lets ROS execute that work.

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

Build from the workspace root. Initialize rosdep once if it has never been configured on this machine (`sudo rosdep init`).

```bash
cd ~/robo_ws
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select tabletop_tools
```

In **each** lab terminal, use this setup. Pick a different unused domain if 72 is taken, and use it consistently throughout the track. Keep the lab on one machine with the Jazzy Fast DDS middleware.

```bash
source /opt/ros/jazzy/setup.bash
source ~/robo_ws/install/local_setup.bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DOMAIN_ID=72 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
unset ROS_STATIC_PEERS
```

In terminal A, run `ros2 pkg prefix tabletop_tools` and expect a path under `~/robo_ws/install`. Run `ros2 run tabletop_tools heartbeat`. In terminal B, use `ros2 topic echo /tabletop/heartbeat --once`. Expect `data: beat N` with a sequence number that may already be above zero. This process publishes test data without a robot or physics simulator. Stop it with Ctrl+C when done.

## Diagnose the first failing layer

If `colcon list` at the workspace root omits the package, check its location and manifest. If building succeeds but `ros2 pkg prefix` fails, check the sourcing order in the run shell. If the prefix is right but `ros2 pkg executables tabletop_tools` omits `heartbeat`, check `console_scripts` and the generated script installation path in `setup.cfg`, then rebuild. If the process starts but echo hangs, check discovery and endpoint matching in [ROS 2 communication](/notes/ros2-communication/).

## Self-check

Why can `python3` import your module from the package's source directory while `ros2 run tabletop_tools heartbeat` fails in a new terminal?

<details>
<summary>Check your answer</summary>
<p>Python can import from its working directory. The ROS CLI needs the installed package marker and executable wrapper, and the shell must be configured to find that installation prefix.</p>
</details>

- [Jazzy Python package scaffolding and entry points](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html)
- [Jazzy parameter descriptor definition](https://raw.githubusercontent.com/ros2/rcl_interfaces/jazzy/rcl_interfaces/msg/ParameterDescriptor.msg)
