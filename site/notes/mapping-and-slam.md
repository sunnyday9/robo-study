---
title: "Build maps and correct drift with SLAM"
topic: "Perception and estimation"
order: "044"
description: "Distinguish mapping from localization, reason about loop closures, and solve a small pose graph with a false-match test."
prerequisites: "Coordinate transforms, calibrated range measurements, state estimation, and basic Python."
minutes: 65
---

## Make a map that survives a second visit

An indoor differential-drive rover records the same wall on two passes. If its wheel odometry drifts between them, the scan endpoints can draw two walls a few centimeters apart. Did the room change, or did the rover place one scan incorrectly? This ambiguity connects the robot's trajectory to the map it builds.

| Problem | Given | Estimated |
| --- | --- | --- |
| Odometry | Incremental motion evidence from wheels, images, or scan alignment | Short-term relative motion and an integrated local pose |
| Localization | A reference map and current observations | Pose in the map's coordinates |
| Mapping with known poses | Observations and their sensor poses | A representation of the scene |
| Simultaneous localization and mapping (SLAM) | Observations and motion constraints | A mutually consistent trajectory and scene model, or a trajectory from which a map can be built |

Wheel odometry is useful between observations and can support smooth local estimates. Revisiting a place can add information about old poses as well as the current one. The lab isolates that correction by solving an entire short trajectory with and without a loop closure. It also shows what a convincing false closure can do.

## Accumulate evidence along a ray

To build a 2D occupancy grid from known poses, choose a resolution in meters per cell and an origin in a fixed frame. For an axis-aligned grid, cell indices come from `floor((coordinate - origin) / resolution)` on each axis. Transform both the sensor origin and each valid endpoint at the beam's acquisition time. Traverse cells between them. A simple opaque hit model adds free evidence before the endpoint, occupied evidence at the endpoint, and leaves cells behind the endpoint alone. A max-range or missing return needs interpretation according to the actual sensor contract. A single horizontal slice can miss overhead and low obstacles. [OctoMap overview of occupancy representations](https://octomap.github.io/) · [ROS LaserScan message](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/LaserScan.msg)

Store each cell's **log odds** `L = ln(p / (1 - p))`. A prior of `p = 0.5` gives `L = 0`. Under a simple cell-wise evidence model, add a positive log likelihood ratio for a hit and a negative one for traversal. For illustration, add `+0.85` for a hit and `−0.40` for free evidence. Two hits and one traversal yield `L = 1.30`, or `p = 1 / (1 + exp(−1.30)) ≈ 0.79`. These increments are modeling choices. Neighboring beams and repeated scans are correlated, so independent cell updates can overstate certainty. Clamp log odds to limit how much evidence is needed to recover after new observations. Keep an observed flag so never observed cells can be distinguished from cells with conflicting evidence.

Grid resolution trades detail against memory and pose sensitivity. A 0.05 m cell will not rescue a scan placed 0.10 m from its true pose. A landmark map stores sparse objects and can be efficient for localization when landmarks are distinctive. A grid makes free-space queries direct, while a pose graph can retain the historical scans needed to rebuild that grid. Choose according to the downstream queries and whether the trajectory can still change.

## Constrain the trajectory with a loop closure

```text
Time order:  [x0] -- m1 --> [x1] -- m2 --> [x2] -- ... --> [x6]
               |                                            |
               +---------- c: proposed revisit ------------+
               ^ fixed anchor               m_i: incremental measurements
```

The nodes are poses at selected acquisition times. Each edge says what relative transform the sensors measured between two poses. For poses `X_i` and `X_j` expressed in a common frame, the predicted relative transform is `inverse(X_i) X_j`. Express the discrepancy to the measured relative pose in local translation and rotation coordinates and weight it with the edge uncertainty. Fix one pose or use a prior to remove the freedom to translate or rotate the entire graph together. This choice of origin provides a reference without surveying the building. An optimizer redistributes residuals across the constrained poses. [GTSAM PoseSLAM tutorial](https://gtsam.org/tutorials/intro.html#41-loop-closure-constraints)

**Data association** decides which observations refer to the same place or landmark. Similar-looking doors and parallel corridors can create plausible but wrong candidates. Search for candidates, verify the relative geometry, and reject alignments supported by too little overlap or by geometry that leaves a direction weakly constrained. A robust loss can reduce the influence of large residuals. A wrong match can still deform the trajectory if it receives strong weight or if a competing match is absent. Once a correction moves historical poses, rebuild or update the map using the corresponding scans at corrected poses. SLAM Toolbox documents a scan-matching and pose-graph workflow that uses scans associated with the graph to construct the map. [SLAM Toolbox architecture](https://github.com/SteveMacenski/slam_toolbox)

## Preserve a continuous local frame

ROS REP 105 defines the tree `map → odom → base_link`. `odom` supplies a continuous local reference that can drift. `map` supplies the longer-term reference, and the estimated robot pose in it may jump as information arrives. Use one authority for `odom → base_link` and one for `map → odom`. If `T_A_B` takes coordinates in B to A, compute the correction at a common time as `T_map_odom = T_map_base × inverse(T_odom_base)`. For a translation-only example at a revisit, a map position of +0.024 m and an odometry position of +0.600 m give a correction of −0.576 m. In 2D with yaw, compose the transforms in order because rotating changes the direction of translations. Compare the two frame traces in replay to catch global corrections accidentally appearing in the local odometry. [ROS REP 105 frames and authorities](https://github.com/ros-infrastructure/rep/blob/master/rep-0105.rst)

## Lab: close an out-and-back trajectory

Save as `sensing-slam.py` and run `python sensing-slam.py`. The synthetic rover travels out and backs along one axis with fixed heading. All displacements are signed meters in that axis. The start is anchored at zero. Odometry ends +0.60 m away from the start, although truth ends at zero. The graph lab inserts an already verified synthetic loop constraint `c = 0 m`, then tries a false association to a feature that suggests `c = −0.80 m`.

Solve for the corrected increments `d_i`. The sum of penalties is `sum((d_i - m_i)² / sigma²) + (sum(d_i) - c)² / tau²`. Here `sigma` is each odometry edge's standard deviation and `tau` is the closure's. Taking the derivative with respect to each `d_i` gives the same correction for every edge because the odometry weights are equal. Summing the derivative equations yields a correction equal to `(sum(m_i) - c) × sigma² / (n × sigma² + tau²)`, subtracted from each `m_i`. This special case needs no numerical solver.

```python
from itertools import accumulate
from math import sqrt
from statistics import mean

truth = [0, 1, 2, 3, 2, 1, 0]
wheel = [1.10, 1.12, 1.08, -0.88, -0.90, -0.92]
sigma, tau = 0.12, 0.06  # assumed standard deviations in meters


def solve(closure):
    correction = 0.0
    if closure is not None:
        correction = ((sum(wheel) - closure) * sigma**2
                      / (len(wheel) * sigma**2 + tau**2))
    return list(accumulate((m - correction for m in wheel), initial=0.0))


for name, closure in [("odometry", None), ("true loop", 0.0), ("false loop", -0.8)]:
    poses = solve(closure)
    rmse = sqrt(mean((x - ref)**2 for x, ref in zip(poses, truth)))
    print(f"{name}: final={poses[-1]:+.3f} m, trajectory RMSE={rmse:.3f} m")
```

Expect the true loop to reduce final error to 0.024 m and the false loop to make trajectory RMSE worse than odometry. Print each corrected pose to see that every past step after the anchor moves. The scores use the same start-aligned reference and time correspondence for all three cases. The fixture illustrates the back end solving fixed associations. In a full stack, measure the front end's accepted and rejected matches against known revisits and lookalikes separately.

On simulator replays, compare timestamp-matched trajectory error in a declared alignment and relative motion error over fixed intervals. Also score wall alignment and occupied/free agreement against surveyed or simulated geometry, and report how much space was actually observed. A good endpoint can hide severe earlier drift. Report results with closure enabled and disabled over repeated routes, and inspect high-impact edges when a closure makes the map worse. A crisp merged map can still put two identical corridors at the same coordinates. Check a route with deliberate lookalikes before considering supervised commissioning.

## Exercise: weaken a questionable loop closure

Change `tau` to 0.60 m. Predict the new endpoint for the true loop. Does assigning more uncertainty solve false association?

<details>
<summary>Check the result</summary>
<p>The total correction is 0.60 × (6 × 0.12²)/(6 × 0.12² + 0.60²), about 0.116 m, leaving the endpoint near +0.484 m. Lower weight reduces either loop's influence, including a true correction. Verify candidate geometry and revisit identity using independent evidence.</p>
</details>

## Exercise: debug a double wall

In replay, two walls are distinct only on runs with tight turns. What comparisons would separate scan skew, a wrong mount pose, and a false closure?

<details>
<summary>Check the investigation</summary>
<p>Compare stopped scans at surveyed poses to check the mount transform. Replay the turns with one pose per scan and then with per-ray timestamps and interpolated poses. Inspect skew within individual scans. Compare the same trajectory and reconstructed grid before and after candidate loop constraints. A sudden change after one accepted match points toward that edge or its weight.</p>
</details>

## What to carry forward

- Use poses and ray evidence to build maps. Keep occupied, observed free, and unknown space distinct.
- Validate loop associations before trusting a pose graph's corrections. Measure both trajectory and map quality.
- Preserve smooth local odometry and expose global corrections through the frame tree. See [frames and clocks](/notes/ros2-frames-and-time/) for timestamped transform lookups.
