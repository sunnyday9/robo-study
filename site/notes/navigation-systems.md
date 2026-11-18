---
title: "Navigation systems"
topic: "Planning and autonomy"
order: "051"
description: "Connect global paths, local control, localization, and recovery, then test why the same path can require different motion decisions."
prerequisites: "Search and motion planning, coordinate frames, and basic feedback."
minutes: 50
---

## Follow a route in a changing hallway

An indoor differential-drive rover has a route to a charging bay. Someone rolls a cart across the next doorway. The route remains meaningful as a statement of intent, but the next velocity command has to account for the cart. A navigation system repeatedly closes that loop. It estimates where the robot is, updates what it thinks is traversable, plans where to go, and tracks progress. Each piece can return a plausible output even when the system as a whole has become inconsistent.

```text
Goal in map -> [global planner] -> path in map -----------+
                      ^                                   v
              global costmap                     [local controller]
                                                          |
Scan at t -> [transform at t] -> rolling local costmap ---+
                                                          |
Odom pose and twist -------------------------------------+
                                                          v
                                  body command v, yaw rate to base

The executive observes progress and can cancel or request a new path.
```

The arrows show the data dependencies. The global planner finds a corridor to the bay. The local controller uses a short horizon to choose motion that tracks the path from the current pose. For the rover, the base command generally contains forward velocity in m/s and yaw rate in rad/s. The base's own wheel feedback loop attempts to achieve that command. A path, a body command, and evidence of actual motion are three different signals. [Feedback control](/notes/pid-feedback/)

## Keep the pose and world model coherent

Write the transform chain as `map → odom → base_link → laser`. The odometry system owns `odom → base_link`. Wheel estimates may drift, but the pose should change continuously. Localization can correct that drift by publishing `map → odom`, so map-frame pose can jump. This makes the map frame appropriate for goals and the odometry frame useful for smooth local feedback. Express a map-frame path in the local frame with a compatible transform and invalidate plan assumptions after large corrections. A scan used to place a cart in a costmap needs a transform at its acquisition time. Stamping the scan with its delivery time can produce an apparent obstacle that moves with the robot. [REP-105 frame definitions](https://raw.githubusercontent.com/ros-infrastructure/rep/master/rep-0105.rst) · [ROS 2 frames and time](/notes/ros2-frames-and-time/)

A **costmap** discretizes traversability. A static layer can encode the building. An observation layer can mark returns and use clear sensor rays to remove stale occupied cells. Unobserved space needs an explicit policy. A route planner may treat it as forbidden when building a known-space route. A moving local window can emphasize fresh data nearby. A footprint describes the body in its base frame, including protrusions. At a candidate pose, rotate and translate the polygon before checking the occupied cells it covers. A disk approximation is easier to check and can block turns that a real rectangle could make. Graded inflation around obstacles gives planners a reason to prefer the middle of a corridor. Check what each plugin does with lethal costs, unknown costs, and polygon checks. These choices determine how the graded field and hard collision rejection interact. [Nav2 Jazzy costmap footprint source](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_costmap_2d/src/costmap_2d_ros.cpp) · [Jazzy inflation source](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_costmap_2d/plugins/inflation_layer.cpp)

## Choose a controller and a recovery policy together

A lookahead path follower steers toward a target ahead on the path. A short lookahead reacts sharply to cross-track error. A long one smooths commands but can cut corners. A rollout controller instead evaluates candidate commands by predicting the rover's motion over a horizon and scoring trajectories for tracking effort, clearance, and progress. Check speed and steering limits, and check collision along the candidate motion. If no command is feasible, distinguish temporary obstruction from persistent failure. A progress check can ask whether the rover has displaced a minimum distance within a time window. A goal check asks whether position and heading are within their tolerances. Set the progress check so that legitimate slow or rotation-only maneuvers have a chance to complete.

Nav2 on ROS 2 Jazzy expresses these roles through planner and controller servers with plugins and a behavior-tree navigator that coordinates actions. Its Jazzy bringup example uses a rolling local costmap in `odom` and a global costmap in `map`. One supplied tree attempts contextual costmap clearing after eligible planner or controller errors and has bounded retries and recovery actions. Read the actual tree and parameters for the version you deploy. In a simulation with a cart still present, clearing an observation layer may briefly hide the cart. Require fresh sensing and a valid footprint check before considering motion again. Analyze the swept area before permitting any recovery with motion in supervised commissioning. [Nav2 Jazzy navigation servers](https://docs.nav2.org/jazzy/getting_started/navigation_concepts/navigation_servers/) · [Jazzy bringup parameters](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_bringup/params/nav2_params.yaml) · [Jazzy replanning and recovery tree](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml)

## Lab: replay local decisions on the same path

Keep the global path fixed and model one straight segment with an immobile cart. The input clearance is the free distance from the rover's front footprint at sensor acquisition, in meters. Assume an upper bound `v` on speed until braking begins, a lower bound `a > 0` on constant braking deceleration, and a residual distance reserve `m`. The modeled clearance budget is `d = v(age + lag) + v²/(2a) + m`. The first term covers travel between acquisition and braking. The second follows from constant-deceleration kinematics. Here the executive can keep tracking or request a stop. A stop request made too late can still exceed the remaining distance.

Save as `replay_nav.py` and run `python replay_nav.py`. The input times are seconds on a synthetic shared clock. The age limit and distances are lab fixtures.

```python
from math import isclose

SPEED, BRAKE, LAG, RESERVE = 0.40, 0.50, 0.05, 0.08
MAX_AGE = 0.30


def evaluate(clearance, age):
    if clearance is None or not 0 <= age <= MAX_AGE:
        return "stop: missing or stale", None
    budget = SPEED * (age + LAG) + SPEED**2 / (2 * BRAKE) + RESERVE
    return ("track" if clearance > budget else "stop: blocked"), budget


cases = [
    ("fresh", 0.30, 0.05, "track", 0.28),
    ("delayed", 0.30, 0.25, "stop: blocked", 0.36),
    ("closer", 0.24, 0.05, "stop: blocked", 0.28),
    ("expired", 0.60, 0.40, "stop: missing or stale", None),
    ("dropout", None, 0.05, "stop: missing or stale", None),
]
for label, clearance, age, expected, expected_budget in cases:
    decision, budget = evaluate(clearance, age)
    assert decision == expected
    if expected_budget is None:
        assert budget is None
    else:
        assert isclose(budget, expected_budget)
    distance = "-" if budget is None else f"{budget:.2f} m"
    print(label, decision, distance)
```

The fresh case tracks with a 0.28 m budget. Delaying the same observation raises that budget to 0.36 m and triggers a stop request. The expired case requests a stop even with a larger reported clearance. This is a CPU model of one decision boundary. Curves, approaching obstacles, actuator faults, and unknown space require additional evidence. For a more faithful simulation, replay a moving obstacle with timestamped transforms and plot clearance, commands, and measured stopping distance on one timeline.

## Test the boundaries before tuning

Start with one empty-map route and repeat it from fixed poses. Measure completion rate, path length, cross-track error, final yaw error, minimum simulated clearance, and observation-to-command latency. Keep the map and robot version fixed. Then insert one disturbance at a known time, such as a blocked corridor, localization jump, frozen scan, or missing transform. Check which subsystem reports the failure first, whether commands cease within the simulated deadline, whether the rover stops in the simulated envelope, and whether retries are bounded. Replay the first failure with the same input order. Compare scan age at costmap update, the pose and footprint the controller queried, and the actual base response before tuning gains or inflation. [ROS 2 bags and testing](/notes/ros2-bags-and-testing/)

## Exercises

1. A log reports 0.30 m of clearance and 0.25 s of age. Compute the speed bound that just meets the modeled budget. Why is changing a velocity setpoint at this instant insufficient evidence?

<details>
<summary>Solution</summary>

Solve `v² + 0.30v − 0.22 = 0` for its positive root, about 0.342 m/s. Tracking in the lab needs a strictly smaller speed bound. The rover may still be traveling at its previous speed after the setpoint changes. Use measured speed and a conservative bound for the delay interval when evaluating the immediate stop.

</details>

2. A rover stops progressing every time localization makes a large correction near the same shelf. Design a replay that distinguishes a real obstacle from a frame error.

<details>
<summary>Solution</summary>

Record the scan stamps, both dynamic transforms, the pose estimate, and the rejected controller candidate. Overlay the transformed scan and swept footprint in `odom`. Compare a run using the acquisition-time transform with one using the latest transform, while holding the raw scan and command history fixed. Check whether the correction coincides with a shifted map-frame route, a misplaced scan, or a consistently occupied region across both replays.

</details>

## Summary

Global planning chooses a route. Local control turns that route and current observations into feasible commands. Timing, frame consistency, footprint geometry, and measured progress govern when to continue, stop, or replan. Validate those boundaries with deterministic replay before testing closed-loop behavior in simulation.
