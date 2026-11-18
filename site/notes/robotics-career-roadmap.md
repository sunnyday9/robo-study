---
title: Build a robotics portfolio and choose a specialty
topic: Professional practice
order: "132"
description: Turn the common core into a role-specific study plan, with project deliverables and practical readiness checks.
prerequisites: None to plan; complete the relevant core lectures before the projects.
minutes: 60
---

## What does working in robotics require?

You rarely build a whole robot alone. A robotics developer needs enough breadth to debug interfaces with colleagues, then depth in the systems they own. Knowing one simulator's menus is narrower than understanding why a robot estimates state, how it enforces limits, and what evidence shows a change improved behavior. On the other hand, memorizing every control or ML algorithm is not a substitute for successfully reproducing and diagnosing a real workflow.

Use this book as a common core with practical exit criteria. A self-study portfolio shows how you think, implement, and validate. It does not certify you to operate equipment, replace supervised practice, or guarantee readiness for every robotics job.

## Study in passes, not feature checklists

```text
 common core: motion + sensing + planning + software verification
                  |
       choose one working problem / project
                  |
       one specialty in depth + one adjacent interface
                  |
       portfolio review + supervised practice where available
```

An example plan is four blocks. They are not calendar promises. Repeat a block if you cannot reproduce the artifact without following instructions line by line.

| Block | Learn and build | Exit criterion |
| --- | --- | --- |
| A: closed-loop basics | [Python robot](/notes/robot-loop/), [measurement](/notes/robot-math-and-measurement/), [frames](/notes/coordinate-frames/), and [kinematics](/notes/robot-kinematics/) | Predict one output by hand, run the fixture, and explain a deliberately wrong unit or sign |
| B: autonomy loop | [Control](/#motion), [estimation](/#sensing), [planning](/#autonomy) | Model one sensor error, predict a route or control response, and characterize what fails |
| C: delivery and reproducibility | [ROS 2](/#ros-2), [simulation](/#isaac-sim), and [infrastructure](/#infrastructure) | Run the intended configuration in a fresh environment and reproduce one failure with a captured trace |
| D: applied project | [Rover](/notes/capstone-rover/) or [tabletop](/notes/capstone-tabletop/), plus an appropriate specialization | Show a baseline, a diagnostic experiment, expected versus observed outcomes, and clearly scoped next work |

For each block, spend at least as much effort on a build or diagnostic as on reading. Maintain a “next question” rather than a long undifferentiated list of unread topics. Example: “Does the estimator keep a world-frame point consistent while the robot turns?” makes a better next session than “study more SLAM.”

## Choose depth based on the work you want to do

| Direction | Go deeper here | Portfolio exercise | Learn beyond this core |
| --- | --- | --- | --- |
| Robot software / integration | ROS 2 workspaces, interfaces, clocks, replay, [the C++ port](/notes/cpp-robot-software/), CI | Run a fresh-room integration scenario and ship a documented regression test for a time or QoS mismatch | C++ ownership and concurrency, build systems, profiling, drivers and middleware internals |
| Controls / manipulation | Kinematics, Jacobians, dynamics, trajectory limits, grasping | Plot tracking and saturation on matched tests; demonstrate a collision-aware pick in simulation | Rigid-body dynamics, optimization, force control and robot-specific tooling |
| Perception / localization | Sensors, calibration, filtering, SLAM, planning interfaces | Reproduce a calibration error, evaluate consistent frame/time handling, and report metrics under sensor faults | Multi-view geometry, probabilistic robotics, robust optimization and real datasets |
| Autonomy / navigation | Mobile models, search, costmaps, behaviors and recovery | Build a simulated rover that handles a detour, localization loss, and an impossible request | Larger maps, traffic coordination, interaction, performance and field validation |
| Robot learning | Demonstrations, processors, objectives, closed-loop evaluation | Compare a scripted baseline and learned policy using matched resets, then explain one representative failure | Statistical evaluation, RL, representation learning, sim-to-real and deployment budgets |
| Embedded / field | Hardware interfaces, C++/timing, commissioning, reliability | Write a fault-handling design backed by timing traces, SIL/HIL plans, and a supervised procedure | RTOS internals, electrical fundamentals, safety engineering, compliance and platform training |

An effective specialty project crosses one adjacent interface. Perception delivers a timestamped pose that navigation can consume; control publishes a deadline or actuator status the supervisor can observe; dataset code explains exactly which clocks and action semantics came from the simulator.

## Write a project handoff somebody else can run

Use a small repository, not screenshots alone. The first page should answer: What problem did you solve? What is the environment? What command runs the baseline? What observations prove it? What does it explicitly not demonstrate?

Keep a compact demonstration and a test matrix. Show normal behavior, one intentional failure, and recovery or safe stopping in simulation. Include run time, version, reset/split choices, success denominator, and at least one failure trace. If another developer needs a credential or a physical lab, supply a fixture or dry-run path that does not require access to it. Include a short decision record for the trade-off you consider most important.

### Try a review exercise before reaching for more tutorials

Choose one completed project and ask a peer to reproduce it from a clean shell. Give them only the repository and README. Record the time to the first meaningful result and the first ambiguous instruction. When they finish, change one constraint—a missing observation, lower velocity limit, or tighter deadline—and ask them to predict the symptom from your contracts. Fix the documentation or tests that prevented prediction, then repeat with a fresh environment.

## Readiness checks

You can name the robot's command, but not the units, limits, source of pose, or update cadence. What should you improve before a larger demo?

<details>
<summary>Review the missing evidence</summary>
<p>Specify one interface at a time: producer, consumer, data type, units, frame, time domain, update expectations and failure behavior. Demonstrate a verified known case before expanding the demo.</p>
</details>

One portfolio video is flawless and another shows a failure and repair. Which makes a stronger engineering example?

<details>
<summary>Review the stronger claim</summary>
<p>The repaired case is usually more informative if you show exact inputs, diagnostic evidence, the changed assumption, and a regression test. Keep the successful result too, but do not omit failures that limit the claim.</p>
</details>

## Use the book as a foundation

There will always be another tool or subfield. Aim to transfer the process: make a small correct model, validate interfaces and assumptions, test what fails, and make the evidence reusable. Use [Modern Robotics](https://modernrobotics.northwestern.edu/nu-gm-book-resource/) or [Underactuated Robotics](https://underactuated.mit.edu/) for deeper mathematics; supplement the tool chapters with their release-specific documentation and supervised lab work for physical systems.
