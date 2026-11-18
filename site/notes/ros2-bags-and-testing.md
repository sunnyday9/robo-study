---
title: "Replay ROS 2 bags and test the graph"
topic: "ROS 2"
order: "064"
description: "Capture a replay fixture, pin launch parameters, and isolate discovery, time, and application failures."
prerequisites: "The Jazzy heartbeat lab, QoS, and ROS time."
minutes: 45
---

## Reproduce a failure without rerunning the simulator

A perception node sometimes stalls after the simulator restarts. Rerunning the scene can change the input, the scheduling, and the clock. Freeze a short input window so you can test those variables one at a time. First make a heartbeat recording with a positive message count. Replay it to a fresh process and check for five increasing sequence values and an advancing consumer clock before a wall-time deadline. Then change just one playback flag and predict which check will fail. The exercise builds a software fixture using ROS 2 Jazzy on Ubuntu 24.04.

## Know which timestamp answers your question

A rosbag2 recording stores serialized messages, topic metadata, and timing information. For ordinary playback in this lab, the timestamp associated with a bag entry schedules its replay. The message's `header.stamp`, when present, has whatever meaning the publisher defined. Use the original acquisition stamp to join a sensor reading to TF. Use the bag timeline to exercise arrival order and pacing. A heartbeat has no header, which makes it useful for separating the transport and clock checks from acquisition-time geometry.

```text
Illustrative capture from one simulation clock (seconds)

                                 Observation A        Observation B
Message header: acquired at          12.000               12.100
Bag entry: recorder clock reads      12.040               12.110
Playback: wall offset at 1x           0.000                0.070
Playback: wall offset at 2x           0.000                0.035
                                      |                    |
TF lookup after either replay        12.000               12.100
```

The offsets are relative to the first entry and idealized. The acquisition interval is 100 ms. The recorder sees entries 70 ms apart on its timeline, so a 2× player targets a 35 ms wall-time gap. Neither playback rate changes the acquisition stamps in the payload. Arrival can still differ from the schedule because subscribers, middleware, and executors are running again. This is why a bag can reproduce recorded inputs while yielding a different downstream callback order or timing.

On a simulated run, `ros2 bag record --use-sim-time` uses the recorder's latest received `/clock` for bag receive timestamps. It waits for clock startup before subscribing to the recorded streams. Select `/clock` explicitly if you want its original messages available for later inspection. With `ros2 bag play ... --clock 10`, the player publishes a generated clock from its playback timeline at the configured frequency and excludes replay of the bag's own `/clock` topic. Keep other clock publishers off this graph and set `use_sim_time` on consumers that should follow the player. A bag captured on a system-time timeline can be replayed with a generated clock, but that cannot repair sim-time headers recorded under a different clock. [Jazzy rosbag2 recording guide](https://github.com/ros2/rosbag2/tree/jazzy#simulation-time) · [Jazzy recorder source](https://raw.githubusercontent.com/ros2/rosbag2/jazzy/rosbag2_transport/src/rosbag2_transport/recorder.cpp) · [Jazzy playback flags](https://raw.githubusercontent.com/ros2/rosbag2/jazzy/ros2bag/ros2bag/verb/play.py)

## Lab — override a parameter, record, and replay

Source `~/robo_ws/lab-env.bash` in every terminal. Stop earlier lab publishers. If `ros2 bag` is unavailable, install `ros-jazzy-rosbag2`. Save this runnable launch file as `~/robo_ws/heartbeat.launch.py`. Pinning the period in a launch file ties the fixture to an inspectable startup configuration. A direct `ros2 run` override is quicker when experimenting on one process. Launch is useful once several nodes must start with coordinated parameters. [Workspace setup](/notes/ros2-workspaces/)

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

Expect a double of 0.25 seconds. Record at least eight seconds after the recorder reports the subscription, then stop recording with Ctrl+C so it can finalize the bag. Stop the live launch in A. Use a fresh output directory name on every new recording. For eight full seconds of steady input, 4 Hz implies roughly 32 samples. Treat that as an estimate, since your stop time and received rate affect the count.

In B, run `ros2 bag info heartbeat_bag`. Check for a positive message count and the expected topic and type. Start the data echo in A and, if you have a third terminal, start the clock echo there. Then start playback in B.

```bash
# A: data observer
ros2 topic echo /tabletop/heartbeat std_msgs/msg/String --once

# C: optional clock observer
ros2 topic echo /clock rosgraph_msgs/msg/Clock --qos-reliability best_effort --once

# B: run from ~/robo_ws
ros2 bag play heartbeat_bag --clock 10
```

Expect a recorded `beat N` and a replay clock sample. Record the actual duration, message count, and one observed payload with your launch configuration. If the count is zero, diagnose the recorder's graph, topic, and QoS first. If the bag contains inputs but echo fails, inspect the player's endpoints. If echo works but time-based logic stalls, check whether the consumer is following one advancing clock. Seeing one `/clock` message establishes delivery to the echo process. An advancing clock in the consumer takes another check. [Jazzy launch guide](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Creating-Launch-Files.html)

## Distinguish discovery failures from replay failures

Run these probes in B while the live heartbeat launch is running in A. Stop the player first if replay is active.

| B's settings | Expected visibility of /tabletop_heartbeat |
| --- | --- |
| `ros2 node list --no-daemon --spin-time 2` | Visible with matching local settings |
| `ROS_DOMAIN_ID=73 ros2 node list --no-daemon --spin-time 2` | Absent if A uses domain 72 |
| `ROS_AUTOMATIC_DISCOVERY_RANGE=OFF ros2 node list --no-daemon --spin-time 2` | Absent with this Fast DDS setup |

These one-command overrides leave B's shell settings intact. Use a different mismatching value if the lab uses 73. If direct listing works but ordinary listing differs, restart the CLI daemon with `ros2 daemon stop` and `ros2 daemon start` in the intended environment. For cross-host DDS setups, compare domain, middleware, discovery range, static peers, and multicast reachability. With no static peers, the lab's `LOCALHOST` range limits discovery to the same machine. Zenoh uses its own discovery configuration. Stop the live launch again before restarting the replay tests. [Jazzy discovery settings](https://docs.ros.org/en/jazzy/Tutorials/Advanced/Improved-Dynamic-Discovery.html)

## Develop the test one boundary at a time

**Start with a data invariant.** Use the capstone's [trace validator](/assets/labs/check_trace.py) and [teaching CSV](/assets/labs/tabletop-trace.csv). Save them together and run these commands from that directory. The second command creates a separate fixture with only the first row's command stamp changed.

```bash
python3 check_trace.py tabletop-trace.csv
sed '2s/,1000000,open/,11000000,open/' tabletop-trace.csv > tabletop-trace-late.csv
python3 check_trace.py tabletop-trace-late.csv
```

The teaching fixture should report `OK: 6 rows across 2 episodes`. The mutated fixture should exit nonzero with a skew error: its first command follows a zero-stamped observation by 11 ms and the default budget is 10 ms. This tests a data rule quickly, with no ROS processes. The capstone requires observation before action across the export pipeline. A row with allowable skew can still contain the wrong action if an exporter paired the wrong samples, so keep a known-value fixture as well.

**Turn the manual echo into a bounded integration probe.** Save the following as `~/robo_ws/check_heartbeat.py`. It uses the installed Jazzy Python libraries. It watches sequence and time separately so a timeout can name the missing evidence. Gaps in the sequence are allowed for this delivery smoke test. A duplicate or decrease is a failure because this particular fixture comes from one uninterrupted publisher run.

```python
import time

import rclpy
from std_msgs.msg import String


def main():
    rclpy.init()
    node = rclpy.create_node('check_heartbeat')
    count = 0
    previous = -1
    first_clock_ns = None
    clock_advanced = False

    def on_beat(message):
        nonlocal count, previous
        prefix, _, suffix = message.data.partition(' ')
        if prefix != 'beat' or not suffix.isascii() or not suffix.isdecimal():
            raise ValueError(f'unexpected heartbeat: {message.data!r}')
        number = int(suffix)
        if number <= previous:
            raise ValueError(f'heartbeat did not increase: {previous} -> {number}')
        previous = number
        count += 1

    try:
        if not node.get_parameter('use_sim_time').value:
            raise SystemExit('FAIL: start the probe with use_sim_time:=true')
        node.create_subscription(String, '/tabletop/heartbeat', on_beat, 10)
        deadline = time.monotonic() + 15.0
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            now_ns = node.get_clock().now().nanoseconds
            if first_clock_ns is None and now_ns > 0:
                first_clock_ns = now_ns
            elif first_clock_ns is not None and now_ns > first_clock_ns:
                clock_advanced = True
            if count >= 5 and clock_advanced:
                print('OK: received increasing heartbeats and observed replay time advance')
                return
        raise SystemExit(f'FAIL: received={count} (need >=5), replay_clock_advanced={clock_advanced}')
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
```

Start the probe in A and the player in B within a few seconds. Start each attempt with a fresh probe and make sure the previous player exited. The delay lets the endpoints discover one another before the first bag message.

```bash
# A
/usr/bin/python3 ~/robo_ws/check_heartbeat.py --ros-args -p use_sim_time:=true

# B (from ~/robo_ws)
ros2 bag play heartbeat_bag --delay 2 --clock 10
```

Once that passes, keep the file, delay, and subscriber settings fixed and omit `--clock 10` in B for one run. This bag contains only heartbeat messages. Expect the probe to count beats and fail with `replay_clock_advanced=False`. If both checks fail, investigate delivery before attributing the failure to the clock. If both pass, inspect `ros2 topic info -v /clock` during playback for another authority. Restore `--clock 10` and confirm success again. The monotonic deadline makes the missing-clock case observable even while ROS time is stopped.

To automate the progression, move process startup and shutdown into a `launch_testing` test on its own ROS domain. Start the probe and player, assert a successful probe exit within a wall-time budget, and check clean process shutdown. Keep the no-clock case as a negative control and assert the clock diagnostic. Register the test for your package and inspect failures with `colcon test-result --verbose` after `colcon test`. The terminal probe already exercises actual message delivery and time when run on Jazzy. The test harness would remove manual startup order and collect evidence for repeated runs. [Jazzy integration testing](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Testing/Integration.html)

## Extend the fixture to stamped observations

Repeat the recording with the synthetic joint publisher and state publisher at +90 degrees from [frames and time](/notes/ros2-frames-and-time/). Record with `ros2 bag record -o tabletop_tf_bag --topics /joint_states /tf /tf_static`. Verify that all three streams have messages. Stop the live publishers before replaying `tabletop_tf_bag` with `--clock 10`, and start a fresh `tf2_echo` observer before the player. Compare the base-to-tool transform against the live checkpoint. If fixed transforms are missing, check bag counts and the recorder and player QoS for `/tf_static`. To receive retained transforms after joining late, both the publisher and subscriber need transient local durability.

The [tabletop capstone](/notes/capstone-tabletop/) adds a stamped observation publisher and an exact-time TF checker. That extends the test beyond delivery to acquisition-time geometry. Keep the Isaac Sim 6.1.0 Franka replay and LeRobot 0.4.3 PushT lab in Python 3.12 as separate experiments unless an explicit adapter provides the dataset contract. Preserve observation-before-action pairing and use one simulation clock authority per graph.

## Exercises

**1. Explain a rate change.** Two messages have acquisition stamps 20 ms apart and bag-entry times 60 ms apart. Predict the nominal wall gap at half speed, the header gap at the subscriber, and which gap you would use to match observations with TF.

<details>
<summary>Solution</summary>
<p>Half speed stretches the 60 ms playback interval to about 120 ms of wall time. The payload's header gap stays 20 ms. Look up TF at each original acquisition stamp. Use stopwatch timings to investigate replay performance separately.</p>
</details>

**2. Debug a nonempty bag.** The probe receives ten increasing beats, then reports `replay_clock_advanced=False`. Changing QoS on the heartbeat topic has no effect. Name the next two probes and explain what they tell you.

<details>
<summary>Solution</summary>
<p>Inspect <code>/clock</code> while playing to check that the intended publisher exists and observe at least two increasing clock values. Then inspect the consumer's <code>use_sim_time</code> setting and its clock reading. This distinguishes a missing or paused playback clock from a consumer that never follows it. The heartbeat counter already establishes delivery on its own subscription.</p>
</details>

## Common misconceptions

- **The bag timestamp replaces the header stamp.** The player schedules serialized messages and preserves their payloads.
- **A nonempty bag guarantees a complete fixture.** Verify the required streams, counts, and QoS, including retained static transforms.
- **Playback resets every consumer.** When seeking or looping, handle clock jumps and clear time-indexed application state so old data cannot leak across a reset.

## Summary

Record a small fixture and document which clock defines its timeline. Start with a data invariant, check actual replay with a bounded subscriber, then remove a required input to prove the check can fail. Add stamped geometry only after delivery and time pass independently.
