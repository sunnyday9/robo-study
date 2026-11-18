---
title: "Start here: learn to build robots, not just run their tools"
topic: Orientation
order: "000"
description: Follow a common robotics core, then choose a role, build projects, and collect evidence of your skills.
prerequisites: Basic Python. No robotics, GPU, or physical robot required to begin.
minutes: 25
---

## What makes software robotics?

A robot senses a physical world, infers enough about it to decide, and acts on it. Its actions change what it sees next. A navigation model can be accurate offline and still send a rover into a bad state because its measurement was late, its destination was unreachable, or its motor could not keep up. Robotics is the engineering of that closed loop under physical, computational, and safety constraints.

This book starts at zero **robotics** knowledge and assumes basic programming. Familiarity with Python and ML is useful, but you do not need to start by installing ROS or training a model. You will first write a small simulated controller you can explain. Then you will work outward through geometry, physics, sensing, planning, robot software, learning, and field practice.

```text
  physical or simulated world
      │ observation + frame + time
      ▼
  sensing → state estimate → plan → feedback → actuator
      ▲                                          │
      └────────── world changes as a result ───────┘

  safety limits, clocks, and test evidence cross every boundary
```

There is no single stack called “robotics.” A manipulator commands joints and handles contact. An indoor mobile robot estimates its pose and navigates around obstacles. An embedded engineer may never train a model but needs to know how sensing and actuation behave under deadlines. The shared idea is to specify and test the interfaces that connect these layers.

## Read the common core, then specialize

| Stage | Study | Evidence you can keep |
| --- | --- | --- |
| First steps | [Robot loop](/notes/robot-loop/), [math and measurement](/notes/robot-math-and-measurement/), [frames](/notes/coordinate-frames/) | A Python run, a deliberately broken run, and an explanation of which assumption changed |
| Foundations | [Motion and control](/#motion), [perception and estimation](/#sensing), [planning and autonomy](/#autonomy) | A known forward/inverse motion case, an estimate from noisy samples, and a checked route |
| Software integration | [Robot software and ROS 2](/#ros-2), [simulation](/#isaac-sim), [infrastructure](/#infrastructure) | A sourced workspace, stamped replay evidence, version manifest, and a repeatable fail/pass test |
| Applied engineering | [Robot learning](/#lerobot) or [field engineering](/#field), plus the relevant core | A measured policy comparison, or a timing, commissioning, and verification plan |
| Portfolio | [Rover project](/notes/capstone-rover/) or [tabletop manipulation](/notes/capstone-tabletop/) | A reproducible demo, test cases, a failure analysis, and a concise handoff |

Read across the common core even if you already know what role interests you. Someone implementing a planner needs enough control theory to understand an infeasible trajectory. Someone training a policy needs enough sensor and timing knowledge to catch a corrupted dataset. After the common core, use the [career map](/notes/robotics-career-roadmap/) to choose depth. Do not try to master every specialization in sequence.

## Use the same development loop in every part

1. **Specify an observable claim.** “At a known joint angle, the tool point is here” is testable. “The robot works” is not.
2. **Build the smallest baseline.** Use a known point, a synthetic topic, a grid, or a tiny rollout. Remove runtime layers that the current claim does not need.
3. **Measure at the boundary.** Record frame, units, time source, run configuration, and what you actually saw.
4. **Break one assumption.** Delay a reading, offset a calibration, remove a transform, or change a deadline. Write down the expected symptom before running it.
5. **Explain the first divergence.** If replay and simulation disagree, find the earliest difference rather than changing all parameters at once.

Keep a notebook with columns for claim, configuration, expected result, actual result, and next diagnostic. A successful run is useful; showing that a negative control fails for the right reason is more useful. Compare the scope of the evidence with the scope of the conclusion.

## Choose what to install and when

You can begin with [browser labs](/demos/) and Python. The common-core examples do not require a GPU. Use the [environment chapter](/notes/infra-environments/) when installing ROS, a simulator, or an ML toolkit. Do not start by trying to make every tool share a Python environment.

ROS 2 is middleware and tooling. Isaac Sim, Gazebo, and MuJoCo answer different simulation questions. LeRobot is a learning toolkit, not a simulator. [The simulator selection chapter](/notes/choosing-a-simulator/) makes the trade-offs explicit before the Isaac-specific labs. The PushT learning path and Isaac tabletop path are separate unless you build and test an adapter between them.

## What completing this book can and cannot prove

The study path targets a practical working foundation: make a prototype, specify its interfaces, test it, debug it, and explain its limits. Reading alone does not provide hardware experience. A simulation pass does not qualify a physical robot or a safety system. For hardware practice, use a supervised lab with an approved platform, training, a commissioning procedure, and an authorized person responsible for operation. Use the field chapters to prepare questions and artifacts, not as a substitute for that supervision.

To close a section, show a small artifact independently: no hints, no copying expected output, and one new fault case. If you cannot explain why a test fails, revisit the relevant boundary. This is a better signal of preparedness than the number of chapters marked complete.

## Check your study plan

You have a laptop without a supported GPU and three evenings before you can access a ROS machine. What do you do first?

<details>
<summary>Compare your plan</summary>
<p>Build and mutate the first Python loop, check a known transform by hand, and run a small planning or estimation example. Bring the expected data contract and failure tests to the ROS machine. Save GPU time for questions that genuinely require simulation rendering or physics.</p>
</details>

A developer says they are ready to operate a physical arm because a simulator task completed. What evidence is still missing?

<details>
<summary>Check the evidence boundary</summary>
<p>Hardware calibration, limits, timing, failure and stop behavior, and supervised commissioning remain separate. The simulator result supports only the stated simulated scenario.</p>
</details>

## References for deeper study

- [Modern Robotics](https://modernrobotics.northwestern.edu/nu-gm-book-resource/) develops motion, forces, planning, and control mathematically.
- [MIT Underactuated Robotics](https://underactuated.mit.edu/) develops dynamics, estimation, and optimization in greater depth.
