---
title: "Capstone: from tabletop replay to imitation"
topic: Capstone
order: "50"
description: Produce an auditable pick-and-place experiment without assuming the simulator, middleware, and learning stack share a data format.
prerequisites: The ROS 2 replay, Isaac Sim scene, and LeRobot dataset chapters. The first gate runs on Python alone.
minutes: 90
---

## The task

In simulation, pick a block from a tabletop and put it into a target zone. Start with a scripted baseline, then assess whether a policy can reproduce the task. Keep narrow interfaces: the simulator owns physics, ROS 2 carries observations and commands, an exporter builds demonstrations, and the learning toolkit consumes the exported contract. You can run the ROS graph on a CPU and use another, supported GPU machine for Isaac Sim.

![Three gated stages: ROS 2 replay, Isaac Sim baseline, and LeRobot training and evaluation. Each stage leaves evidence before advancing.](/assets/capstone-gates.svg)

## Gate 1 — align a replay before collecting data

First, [try the timestamp lab](/demos/#clock-lab). The [ROS 2 replay chapter](/notes/ros2-bags-and-testing/) covers recording and replay with a heartbeat. Here you will add stamped observations and TF. These scripts publish only synthetic observations, transforms, and clock; use the [isolated Jazzy shell setup](/notes/ros2-workspaces/) in all terminals.

Download the [trace publisher](/assets/labs/publish_tabletop_trace.py) and [replay checker](/assets/labs/check_tabletop_replay.py). Run the following from the download directory, keeping both terminals in the same directory. Stop the recorder after several seconds of data, then stop the publisher. Use a fresh bag directory on retries.

```bash
# Terminal A
/usr/bin/python3 publish_tabletop_trace.py
# Terminal B
ros2 bag record --use-sim-time -o tabletop_fixture --topics /clock /tf /tabletop/observation
```

Run `ros2 bag info tabletop_fixture` to confirm all three streams have messages. Start the checker first, then start the player well before the checker's 25-second wall-time deadline:

```bash
# Terminal A
/usr/bin/python3 check_tabletop_replay.py --ros-args -p use_sim_time:=true
# Terminal B
ros2 bag play tabletop_fixture --clock 20
```

**Expected:** `OK: 5 stamped poses transform to (2, 2) m`. The replay player is the only clock authority, and the checker uses each message's header stamp instead of the latest transform. It is specialized to this fixture's planar rotation and local point. If it times out, check graph visibility, bag counts, and the timestamp interval available on `/tf`. Do not substitute the time of receipt to make the check pass.

Write the capture contract before writing an exporter:

| Field | Example contract |
| --- | --- |
| Episode | Unique episode ID; new ID after each reset |
| Timestamp | Episode-relative integer nanoseconds, one clock domain; retain original source stamps separately |
| State | Joint order from a saved manifest; joint angles in radians |
| Camera | Identified stream, frame, calibration, color order, shape and resize rule |
| Command | Absolute joint-position targets in radians plus gripper convention; not torques or measured states |
| Pairing | Capture observation before action; record command and acquisition stamps; explicitly bound skew and mark missing data |
| Outcome | Success, failure, or timeout; keep failures in evaluation records |

**Pass:** Confirm that time is increasing within each episode, that stamps and frames are interpretable, and that you can trace one observation to the exact command row that followed it.

### A CPU-only contract check

Download [the validator](/assets/labs/check_trace.py) and [a teaching trace](/assets/labs/tabletop-trace.csv) into the same directory. Then run:

```sh
python check_trace.py tabletop-trace.csv
```

Expected: `OK: 6 rows across 2 episodes`. Try moving one command stamp earlier than its observation or duplicating one frame number; the validator should fail. This is a CSV fixture, **not** a real recording or a LeRobot dataset. It does not validate image contents, TF, units, or physics. A deliberate row shift can still pass structural checks if the stamps are rewritten; inspect motion and labels together using the [alignment lab](/demos/#alignment-lab).

## Gate 2 — establish the simulated baseline

Start with the packaged Franka pick-and-place scene in the [Isaac Sim scene chapter](/notes/isaac-scene/). Its ground plane is the tabletop abstraction. Get the shipped sequence working before adding furniture or a custom robot. Debug the controller in the simulator before introducing the bridge.

Define success before running: for example, the block remains in the target zone after release and settling, within the time budget, without disallowed contact. Log per-trial seeds, block start pose, scene and asset versions, step rate, controller configuration, success, and failure stage. Save a short video for at least one success and one failure.

**Pass:** Report successes over all predeclared trials, including crashes and timeouts. If the scripted controller fails often, debug contacts, timing, or controller targets before collecting training demonstrations.

## Gate 3 — export, train, then evaluate

Use the [LeRobot data chapter](/notes/lerobot-data/) to plan mapping and the [training chapter](/notes/lerobot-training/) to run a versioned baseline. A rosbag is not a LeRobot dataset. Isaac Sim data reaches LeRobot only through an explicitly supported integration or an adapter that generates the expected keys, shapes, timing, and action convention. In the absence of that adapter, train and evaluate the documented LeRobot lab on its own dataset and compatible environment; label the result separately rather than calling it Isaac-to-LeRobot.

1. Save the training/validation split by **episode or scene group**, not frame. Preserve the same camera transforms and feature order at inference.
2. Overfit a small training subset to check data flow; then compare held-out behavior and verify normalization uses training data.
3. If you have a matching closed-loop adapter, run the policy and scripted baseline on the same held-out reset list. Report successes and denominators, timeout and safety-stop counts, and a description of common failures. If you only have offline validation, report offline loss and explicitly state that closed-loop success is unknown.

**Pass:** Another reader can identify the data version, split, policy checkpoint, simulator version, evaluation configuration, and result denominators. They can tell which artifacts were actually produced and which steps remain unverified.

## Self-check

A model gets low offline action error but drops the block after lifting. What do you investigate before increasing model capacity?

<details>
<summary>Check your answer</summary>
<p>Inspect timestamp pairing around contact, action units and gripper conventions, observation preprocessing, and closed-loop timing. Compare the same trial with the scripted controller, and inspect whether the training episodes cover the failure state. Offline error alone does not validate recovery or stability.</p>
</details>
