---
title: "Replay ROS 2 bags and test the graph"
topic: "ROS 2"
order: "13"
description: "Capture a replay fixture, pin launch parameters, and isolate discovery, time, and application failures."
prerequisites: "The Jazzy heartbeat lab, QoS, and ROS time."
minutes: 45
---

## Treat the bag as an input fixture

A rosbag2 recording stores serialized messages, topic metadata, and timing information. The timestamp used to schedule replay is separate from a message's own `header.stamp`. On a simulated run, start the recorder with `--use-sim-time` to timestamp bag entries using its latest received `/clock`. It waits for the first clock update before writing messages. Replay with `--clock` generates a clock from the replay timeline and excludes replay of a recorded `/clock` topic. This leaves the original header stamps intact. Set `use_sim_time: true` on consumers that should follow replay time, and keep other clock publishers off that graph. [Jazzy rosbag2 recording guide](https://github.com/ros2/rosbag2/tree/jazzy#simulation-time) · [Jazzy playback flags](https://raw.githubusercontent.com/ros2/rosbag2/jazzy/ros2bag/ros2bag/verb/play.py)

## Lab — override a parameter, record, and replay

Use the [workspace setup](/notes/ros2-workspaces/) in every terminal. Stop earlier lab publishers. If `ros2 bag` is unavailable, install `ros-jazzy-rosbag2`. Save this runnable launch file as `~/robo_ws/heartbeat.launch.py`.

```python
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='tabletop_tools',
            executable='heartbeat',
            parameters=[{'period_s': 0.25, 'use_sim_time': False}],
        ),
    ])
```

Launch declares the process and its startup values. The node declares parameter types and reads `period_s` when it creates its timer, so this example makes the period read-only. Start `ros2 launch ~/robo_ws/heartbeat.launch.py` in terminal A. Inspect the live parameter and record the topic in B.

```bash
ros2 param get /tabletop_heartbeat period_s
cd ~/robo_ws
ros2 bag record -o heartbeat_bag --topics /tabletop/heartbeat
```

Expect a double of 0.25 seconds. Record for several seconds after the recorder reports the subscription, then stop recording with Ctrl+C. Stop the live launch in A. Use a fresh output directory name on every new recording.

In B, run `ros2 bag info heartbeat_bag`. Check for a positive message count and the expected topic and type. Start the data echo in A and, if you have a third terminal, start the clock echo there. Then start playback in B.

```bash
# A: data observer
ros2 topic echo /tabletop/heartbeat std_msgs/msg/String --once

# C: optional clock observer
ros2 topic echo /clock rosgraph_msgs/msg/Clock --qos-reliability best_effort --once

# B: run from ~/robo_ws
ros2 bag play heartbeat_bag --clock 10
```

Expect a recorded `beat N` and a replay clock sample. This is a software-only replay. If the count is zero, diagnose the recorder's graph, topic, and QoS before debugging playback. If messages arrive but clock-based logic stalls, check clock publication and `use_sim_time` on that consumer. [Jazzy launch guide](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Creating-Launch-Files.html)

## Distinguish discovery failures from replay failures

Run these probes in B while the live heartbeat launch is running in A. Stop the player first if replay is active.

| B's settings | Expected visibility of /tabletop_heartbeat |
| --- | --- |
| `ros2 node list --no-daemon --spin-time 2` | Visible with matching local settings |
| `ROS_DOMAIN_ID=73 ros2 node list --no-daemon --spin-time 2` | Absent if A uses domain 72 |
| `ROS_AUTOMATIC_DISCOVERY_RANGE=OFF ros2 node list --no-daemon --spin-time 2` | Absent with this Fast DDS setup |

These one-command overrides leave B's shell settings intact. If direct listing works but ordinary listing differs, restart the CLI daemon with `ros2 daemon stop` and `ros2 daemon start` in the intended environment. For cross-host DDS setups, compare domain, middleware, discovery range, static peers, and multicast reachability. With no static peers, the lab's `LOCALHOST` range limits discovery to the same machine. Zenoh uses its own discovery configuration. [Jazzy discovery settings](https://docs.ros.org/en/jazzy/Tutorials/Advanced/Improved-Dynamic-Discovery.html)

## Turn the smoke check into a test

Unit-test pure episode parsing with a tiny fixture and known output. For integration, use `launch_testing` to start real ROS processes on a test-specific domain. Assert receipt of the expected type and increasing sequence within a bounded wall-time deadline, then check clean shutdown. Inspect registered test results with `colcon test-result --verbose` after `colcon test`. The manual lab above checks one observable path. [Jazzy integration testing](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Testing/Integration.html)

Repeat the recording with the synthetic joint publisher and state publisher from [frames and time](/notes/ros2-frames-and-time/). Record with `ros2 bag record -o tabletop_tf_bag --topics /joint_states /tf /tf_static`. Check that all three topics have messages. Stop the live publishers before playing `tabletop_tf_bag` with `--clock 10`, then compare the replayed base-to-tool transform against the live checkpoint. If fixed transforms are missing, inspect the bag and the recorder and player QoS for `/tf_static`. Late joiners need transient local durability on both ends. Start the TF observer before playback so it has time to discover the player.

In the [tabletop capstone](/notes/capstone-tabletop/), repeat the bag workflow with a supplied stamped observation and TF publisher. This chapter's heartbeat has no header; it checks delivery and replay, not sensor-time geometry. A later simulator capture still needs its own explicit dataset export step.

## Self-check

You replay a nonempty bag. A sim-time consumer discovers its inputs, but its time-based timer never fires. What do you test first?

<details>
<summary>Check your answer</summary>
<p>Check that the consumer has received an advancing /clock from the one intended authority. A sim-time timer can stall before the first clock message or during a clock pause even when the data topics are visible.</p>
</details>
