---
title: "Start here: how the robotics stack fits together"
topic: Orientation
order: "00"
description: Pick a CPU-first route, learn the boundaries between the tools, and know what to check before moving to a GPU.
prerequisites: Python, data structures, and basic machine learning.
minutes: 25
---

## Think in interfaces

You already know how to write a Python program and train a model. The new part is that a robot’s inputs have **frames, timestamps, and physical units**, and a control decision has to arrive in time. A model that passes an offline check can still fail if its input comes from the wrong frame or its actions arrive late.

| Layer | What it owns | What to verify |
| --- | --- | --- |
| ROS 2 | A graph of processes exchanging typed messages | Names, types, discovery, QoS, frames and timestamps |
| Isaac Sim | A simulated world, robot dynamics, and virtual sensors | Asset versions, joint drives, physics/render rates and clock |
| LeRobot | Demonstration datasets, policy training, and evaluation tools | Episode boundaries, feature order, action semantics, splits and metrics |
| Infrastructure | The environment that makes the other layers reproducible | OS, drivers, runtimes, networking, storage and run manifests |

Simulation is not the same as learning. **Isaac Sim** is the simulator used in this guide. **Isaac Lab** is a separate framework for constructing robot learning environments; when you need it, check that the Lab version supports the simulation backend and release you choose. **LeRobot** is a learning toolkit: it can collect, train and evaluate, but it still needs a source of observations and actions. The course uses PushT for its versioned LeRobot labs rather than assuming an Isaac bridge is a dataset converter.

## Pick your route

1. **Browser and Python only.** Do the [browser labs](/demos/) and the CPU-only contract check in the [capstone](/notes/capstone-tabletop/). No robot, CUDA, or ROS install is required for these.
2. **ROS 2 first.** Use [the workspace lab](/notes/ros2-workspaces/) on the Jazzy/Ubuntu 24.04 reference path. Learn to inspect a graph and replay a recording before adding a simulator.
3. **Add simulation and learning independently.** Follow the [Isaac Sim requirements check](/notes/isaac-environment/) before choosing a GPU host. Start the [LeRobot track](/notes/lerobot-data/) with offline data, then use the versioned environment later for evaluation.
4. **Combine evidence, not environments.** Use the [infrastructure guide](/notes/infra-environments/) to record the environment of each process. The capstone’s stages can run on different machines, with replay and datasets moving between them as artifacts.

## How to work through a lecture

Start with a prediction. If the experiment changes a coordinate convention, write down where one known point should appear. If it changes a queue, write down which delays or drops you expect. This gives you an observable claim and prevents a troubleshooting session from becoming a series of unexplained configuration changes.

Then work in three passes:

| Pass | What you do | What you keep |
| --- | --- | --- |
| Understand | Trace a concrete example by hand and explain the units, time source, and data direction. | A diagram, a calculation, or two written invariants. |
| Reproduce | Run the smallest relevant development lab unchanged. Compare the result against the stated checkpoint. | Command, version, output, and whether it matched. |
| Transfer | Change one condition or break one assumption, predict the symptom, and use evidence to diagnose the result. | Prediction, observation, explanation, and corrected result. |

Do not skip the small probe to get to the full demo. A whole pipeline has too many moving parts. If a camera image does not reach a model, a graph probe can distinguish a missing publisher from incompatible QoS. A pinned saved frame can distinguish a decoder problem from live transport. A test that crosses both at once rarely locates the failure.

Keep a development notebook. For each experiment, record the smallest configuration that reproduced it, one observable invariant, and the outcome. Distinguish **expected** from **measured**. If a lecture uses a fixture or illustrative trace, mark it as such. If a runtime is unavailable, note what a future live test would add rather than filling the gap with an assumption.

## Follow one observation from source to decision

```text
simulate time and contacts
    └─▶ capture timestamped observation
            └─▶ publish typed message / transform
                    └─▶ record raw evidence / export episode
                            └─▶ normalize + predict action
                                    └─▶ apply command and measure outcome
```

At the camera boundary, pretend the simulator captures at 1.000 s but the subscriber receives it 40 ms later. At the data boundary, the observation belongs to its acquisition time, not the arrival time. At the inference boundary, even a correctly labelled tensor can be too stale to act on. Inspecting each boundary with the same sample ID is much more useful than averaging all delay into a single system metric.

The pipeline above is a mental model, not an automatic integration. The course deliberately separates the first ROS replay, the Isaac simulated baseline, and the versioned LeRobot experiment. You can verify each part, then attempt an adapter with agreed timing, coordinate frames, feature order, action semantics, and reset boundaries.
## Plan three development milestones

**Milestone 1: a reliable replay.** Own a small Python ROS package, a synthetic topic, and a deterministic observation example. Write a probe that can tell apart missing delivery, a missing replay clock, and an invalid transform at a known timestamp. Your acceptance test is a second terminal that can reproduce the result from a clean shell. Reopen the [workspace](/notes/ros2-workspaces/), [frames](/notes/ros2-frames-and-time/), and [replay](/notes/ros2-bags-and-testing/) lectures when that contract breaks.

**Milestone 2: a baseline that moves the block.** Keep the scene, asset references, reset pose, and expected success predicate together. Your acceptance test is a short simulated trial that records whether the cube actually lifts and remains at the target after release. Reaching the gripper's target pose is not enough. First establish this in [the Isaac scene](/notes/isaac-scene/) before comparing sensor behavior through [the bridge](/notes/isaac-ros-bridge/).

**Milestone 3: an evaluation another developer can interpret.** Audit demonstrations and normalize on the training split, then verify that a checkpoint can consume a real batch and make valid actions. Keep the original demonstration convention when evaluating. Run the [LeRobot PushT path](/notes/lerobot-evaluation/) independently of Isaac until an adapter exists. Your acceptance test is a report where someone can distinguish which data, simulator, policy, and test conditions produced each number.

Each milestone should generate a small artifact before you attempt the next. Reproduce the failure at the earliest stage that owns it. A decoder cannot repair a clock mismatch, and additional demonstrations cannot fix a controller that sends the wrong command units.

## Know when to advance

Before using a simulator, explain the difference between a ROS message header stamp and the time a subscriber receives the message. Before training, show that observation and action rows refer to the intended step. Before claiming a policy works, compare it with a baseline on held-out closed-loop trials. A passing check at one layer doesn’t prove the next one works.

This is a simulation-first course. It does not teach safe physical commissioning; do not send replay or unvalidated policy commands to a physical robot. Treat missing hardware or GPU results as untested, not failed.

<details>
<summary>Check your understanding</summary>
<p>If a camera image appears in ROS 2 but a policy acts on stale data, start by comparing acquisition, receipt, and inference times in their known clock domains. Changing the model or GPU configuration before measuring the delay can hide the real problem.</p>
</details>

## Transfer exercise: choose the first milestone

You have a Windows laptop with Python but no supported local Isaac GPU. What do you build in week one? What evidence should you produce before renting compute or adding the simulator?

<details>
<summary>Check the staged plan</summary>
<p>Start with the browser and Python contract labs. Then use the supported Jazzy CPU path to make a synthetic message stream, observe it, and capture and replay it. Keep a trace and a simple check of frame, timestamps and units. Move only the simulation workload to a supported GPU host when you can say what the bridge should publish and how you will verify it.</p>
</details>

## What to carry forward

- Treat data interfaces as engineering contracts, not just compatible arrays.
- Make the first milestone small and observable. Separate environments until you have a reason to connect them.
- Aim to explain a failure from evidence. A green command alone is not the end of a lecture.

## Official references

- [ROS 2 Jazzy: Ubuntu binary packages](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/Ubuntu-Install-Debs.rst)
- [Isaac Lab: installation and backend compatibility](https://isaac-sim.github.io/IsaacLab/main/source/isaaclab/installation.html)
- [LeRobot documentation and supported environments](https://huggingface.co/docs/lerobot/en/index)
