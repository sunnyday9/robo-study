---
title: "Capstone: build and diagnose an indoor rover"
topic: Capstone
order: "130"
description: Deliver a small navigation stack with a replayable trace, known failure cases, and a staged path toward ROS 2 integration.
prerequisites: Robot loop, mobile models, state estimation, and motion planning. The first lab uses Python only.
minutes: 160
---

## Define the engineering deliverable

Design a simulated indoor rover that can reach a marked goal, take a detour when a corridor closes, and stop rather than issue an invalid command when there is no route or state is stale. The project is about reasoning across interfaces, not implementing every production component at once.

```text
map + estimated pose + goal ─▶ planner ─▶ path
 observed obstacles / age ──▶ safety gate and task executive
 path + pose ────────────────▶ local controller ─▶ bounded drive command
 drive + environment ────────▶ next observation ─▶ trace / evaluator
```

Your deliverable is a runnable repository, an experiment manifest, and a failed-run analysis. Passing a grid is the beginning, not a claim that a real platform is safe to operate.

## Gate 1: develop the route and supervisor on a grid

Download [rover_project.py](/assets/labs/rover_project.py) and save it in an empty project directory. It models the rover as a **point** with four-neighbor unit-cost motion. Every accepted command moves one cell immediately. Its map gives perfect occupancy; its observation is the current cell. This design removes all estimation and control difficulty so you can reason about the planner and stopping policy independently.

```text
   col:  0 1 2 3 4 5 6 7
row 0    . . . # . . . .
row 1    . . . # . . . .
row 2    S . . o . . . G   o closes at tick 2 in the blocked case
row 3    . . . # . . . .
row 4    . . . # . . . .
row 5    . . . . . . . .   bottom opening remains unless sealed
```

Look at the core update. A battery of scenarios changes just one condition relative to the baseline when possible. At each tick, apply the synthetic map update, test freshness, plan on the current map, check the immediate edge, accept one movement, and log the *pre-action* position. The graph is small enough for breadth-first search; A* is a performance extension, not required to get a correct result. Compare with [search and motion planning](/notes/search-and-motion-planning/).

![A grid diagram shows the direct path crossing a newly blocked cell. The replanned route turns at tick 2, crosses below the wall, and returns to the goal.](/assets/rover-detour.svg)

```sh
python rover_project.py --scenario baseline --trace
python rover_project.py --scenario blocked --trace
python rover_project.py --scenario sealed
python rover_project.py --scenario stale
python rover_project.py --scenario blocked --budget 12
```

| Trial | Expected end | What it tests |
| --- | --- | --- |
| Baseline | Goal in 7 commands | Clear corridor and minimum steps on the grid |
| Blocked | Goal in 13 commands | Replanning around the bottom opening before crossing the closed cell |
| Sealed | No route after 2 commands | Stop when both crossings are closed |
| Stale | Stale observation after 2 commands | Reject motion at the first stale observation, even with a route |
| Blocked with budget 12 | Deadline after 12 commands | Time budget and planning success are separate conditions |

Do not patch the planner until you know which acceptance test failed. For example, if the blocked case takes seven steps, check whether the map revision changed at tick 2 and whether the controller reused a path planned before that update. If a route exists but budget expires, record time or distance remaining. If you add caching, make map version and goal part of the cache key and recheck edges after updates. Run all five cases after every change.

## Gate 2: replace grid moves with continuous driving

Keep the map coordinates and planner tests. Define cell centers, resolution, grid origin, and map axes. Add the robot footprint or a conservative inflated obstacle map. A four-connected path through free cells is not yet a drivable trajectory; translate it into headings and local motion targets. Use the [differential-drive model](/notes/mobile-robot-models/) for commanded wheel velocities, and enforce linear and angular limits at the local controller boundary.

1. Use perfect pose first. Verify a straight segment and one turn at known positions before trying the whole path. Keep controller and physics intervals in seconds.
2. Replace true pose with a noisy or drifting estimate. Record ground truth only as evaluator evidence; the controller must not read it.
3. Inject exactly one disturbance per comparison: a delayed scan, a fixed wheel-scale error, or a blocked cell. Log goal residual, minimum modeled clearance, command age, and the first unexpected transition.
4. Restore nominal input and rerun. Publish the first failing trace and your fix, not just a screen recording of a successful run.

Download [rover_continuous.py](/assets/labs/rover_continuous.py) into the same folder as `rover_project.py`. This starter implements a **continuous kinematic point** model, not contact dynamics or a physical footprint. It takes the static detour from Gate 1 and follows each cell center using rotate-then-drive waypoints and wheel-rate limits. The controller sees only its odometry estimate. The simulation uses true pose to score arrival and point-to-wall distance at the sampled states.

```sh
python rover_continuous.py
python rover_continuous.py --encoder-scale 1.10
```

The baseline measured a true goal error of 0.018 m and minimum sampled wall clearance of 0.193 m. With a 10% encoder scale error, the rover still passed the 0.08 m goal criterion but its minimum clearance shrank to 0.067 m. That difference would matter to a robot with an 0.08 m footprint radius; passing the final goal check alone would hide it. The fixture checks sampled points, so it is not a swept collision test either. Your extension is to add footprint and edge validation, then introduce an independent pose fix as a separate experiment. Keep the original two results as regressions.

## Gate 3: integrate through ROS 2 without changing the experiment

Use the [ROS workspace](/notes/ros2-workspaces/) and [bag replay](/notes/ros2-bags-and-testing/) chapters to carry the same fixture through message boundaries. If using a ROS-compatible simulator, choose a supported pairing from [the simulator guide](/notes/choosing-a-simulator/). Keep playback on an isolated test graph without physical controllers.

Write and inspect a contract before choosing topics. Which node owns the transform? Is the pose stamped at acquisition? What happens when a plan is older than the current map or no velocity command arrives? Set one simulation clock. Capture observations and decisions for replay, with exact frame names and units. Once point-to-point commands work, compare your design to [a navigation stack](/notes/navigation-systems/); learn which component supplies planning, localization, and tracking rather than treating middleware as the algorithm.

A physical extension is optional and separate. Prepare a supervised commissioning plan using [the field guide](/notes/commissioning-and-diagnostics/). A simulated timeout or zero target is not a hardware safety function.

## What to put in a portfolio

- A small architecture diagram naming each owner of state, transform, and command.
- A table of baseline and fault runs with exact expected outcomes and actual results.
- One annotated trace showing the first divergence and the narrowest fix.
- A reproduction command and environment manifest. State explicitly which gates were completed.
- A follow-up design choice: e.g., trade slower progress for more clearance, or add an external pose source to distinguish drift from tracking error.

## Exercises

Why might a point rover pass through a one-cell doorway while an inflated-footprint planner reports no path?

<details>
<summary>Check physical feasibility</summary>
<p>The point rover has no extent. Inflation reserves space for the robot and uncertainty. Check map resolution and footprint dimensions rather than reducing margins solely to make the test pass.</p>
</details>

The blocked case reaches the goal in 13 commands, but a new log says the first proposed move into the blocked cell was rejected by a downstream constraint. Is that an equivalent pass?

<details>
<summary>Check the interface failure</summary>
<p>No. It establishes containment by the downstream constraint, but the upstream route or freshness check is wrong. Keep the rejection as evidence, then inspect which map revision the planner saw at the decision tick.</p>
</details>

## What to carry forward

Start with testable graph and behavior invariants. Add continuous motion, estimation, middleware, and hardware in separate gates only as evidence warrants it. The useful engineering artifact is a repeatable explanation of success and failure.
