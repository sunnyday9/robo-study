---
title: "Start here: how the robotics stack fits together"
topic: Orientation
order: "00"
description: Pick a CPU-first route, learn the boundaries between the tools, and know what to check before moving to a GPU.
prerequisites: Python, data structures, and basic machine learning.
minutes: 15
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

## Know when to advance

Before using a simulator, explain the difference between a ROS message header stamp and the time a subscriber receives the message. Before training, show that observation and action rows refer to the intended step. Before claiming a policy works, compare it with a baseline on held-out closed-loop trials. A passing check at one layer doesn’t prove the next one works.

This is a simulation-first course. It does not teach safe physical commissioning; do not send replay or unvalidated policy commands to a physical robot. Treat missing hardware or GPU results as untested, not failed.

<details>
<summary>Check your understanding</summary>
<p>If a camera image appears in ROS 2 but a policy acts on stale data, start by comparing acquisition, receipt, and inference times in their known clock domains. Changing the model or GPU configuration before measuring the delay can hide the real problem.</p>
</details>

## Official references

- [ROS 2 Jazzy: Ubuntu binary packages](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/Ubuntu-Install-Debs.rst)
- [Isaac Lab: installation and backend compatibility](https://isaac-sim.github.io/IsaacLab/main/source/isaaclab/installation.html)
- [LeRobot documentation and supported environments](https://huggingface.co/docs/lerobot/en/index)
