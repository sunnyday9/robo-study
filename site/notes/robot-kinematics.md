---
title: Robot kinematics
topic: Motion and control
order: "030"
description: Predict where a tabletop arm reaches, choose among inverse solutions, and detect where it loses a direction of motion.
prerequisites: Coordinate frames, trigonometry, and Python. Partial derivatives are helpful.
minutes: 55
---

## From a target to a joint configuration

A tabletop arm has to bring a marker tip to a dot. The dot is specified in meters from the base, while the arm accepts joint angles. **Kinematics** connects those descriptions using geometry. It can tell you whether a target is reachable and how fast the tip moves for given joint speeds. Questions about the torque needed to move the arm or how the marker behaves on contact belong to dynamics.

Start with a horizontal arm with two revolute joints, called a **2R arm**. A revolute joint rotates about an axis. The shoulder angle `q1` is measured from base +X, and the elbow angle `q2` is measured from the first link's direction. The arm has two **degrees of freedom** (DoF) because two independent coordinates specify its configuration. Counting coordinates in a data structure can give the wrong answer. For example, `(cos(q1), sin(q1))` stores two numbers with one constraint, so it represents one DoF. [Modern Robotics on degrees of freedom](https://modernrobotics.northwestern.edu/nu-gm-book-resource/2-2-degrees-of-freedom-of-a-robot/)

**Configuration space** contains the possible joint configurations. For unrestricted angles it wraps every full turn on each axis. With physical joint stops, use the actual allowed intervals when comparing angles or checking a move. **Task space** describes what the job asks you to control, here the tip's `(x, y)` in the base frame. The **workspace** for this task is the reachable subset of that plane. With full rotations and no obstacles, it is an annulus with inner radius `abs(L1 - L2)` and outer radius `L1 + L2`. Actual stops and obstructions further constrain where the arm can operate. Changing the task to include marker orientation adds a third requested component, which this two-joint arm cannot independently specify. [Modern Robotics on task space and workspace](https://modernrobotics.northwestern.edu/nu-gm-book-resource/2-5-task-space-and-workspace/)

## Build the pose from known frames

<figure class="lesson-figure">
  <a href="/assets/figures/two-ik-solutions.svg"><img src="/assets/figures/two-ik-solutions.svg" width="640" height="353" loading="lazy" decoding="async" alt="Two arm configurations share one base and one tip target. The solid route has its elbow above the X axis and the dashed route has its elbow below."></a>
  <figcaption>Both joint solutions reach the same point. Choose a branch using the starting pose, joint limits, and obstacles—not the tip position alone.</figcaption>
</figure>

Use the convention from [Coordinate frames](/notes/coordinate-frames/). `T_A_B` converts coordinates from B to A. A planar rigid pose belongs to **SE(2)** and can be stored as a 3×3 homogeneous matrix with a 2×2 rotation `R`, a two-component translation `t`, and a final row `[0, 0, 1]`. **SE(3)** is the spatial analogue with a 3×3 proper rotation, three-component translation, and final row `[0, 0, 0, 1]`. The rotation columns are unit perpendicular axes with determinant +1. In both cases the transforms compose as rigid motions, and their inverse has rotation `Rᵀ` and translation `−Rᵀt`. [Modern Robotics on homogeneous transforms](https://modernrobotics.northwestern.edu/nu-gm-book-resource/3-3-1-homogeneous-transformation-matrices/)

For the arm, start at the shoulder frame and rotate by `q1`. The next origin is `L1` along the turned shoulder's +X. Rotate there by `q2`, then move `L2` along the turned elbow's +X to the tip. Multiply the transforms in that written order to obtain `T_base_tip`. Apply it to the tip origin to obtain `p_base`. To solve a target provided in an already calibrated task frame, first apply `T_base_task` to the target. For moving frames, use the transforms and joint states at the relevant observation time.

```text
View from above, +Y up and +X right (sketch is not to scale)

              elbow B
             /       \
         L1 /         \ L2
           /           \
 shoulder +             * shared target (x, y)
           \           /
         L1 \         / L2
             \       /
              elbow A
```

The two bent configurations reach the same tip point from different sides of the shoulder-to-target line. Their tip orientations generally differ. For either configuration, **forward kinematics** (FK) adds the two link displacements in base coordinates:

```text
x = L1 cos(q1) + L2 cos(q1 + q2)
y = L1 sin(q1) + L2 sin(q1 + q2)
tip heading = q1 + q2   (modulo a full turn)
```

## Solve for both elbows and choose a branch

**Inverse kinematics** (IK) starts from a desired task value. At distance `d` from the shoulder, the cosine law gives `d² = L1² + L2² + 2 L1 L2 cos(q2)`. Solve for `c = cos(q2)`. A value outside `[-1, 1]` beyond numerical tolerance means the target is unreachable for the geometric model. In the interior, `sin(q2)` can be either sign. Use `atan2(sin(q2), c)` to recover the signed angle. The shoulder heading is the bearing `atan2(y, x)` minus the bearing of the tip in the turned shoulder frame, `atan2(L2 sin(q2), L1 + L2 cos(q2))`. At the annulus boundaries the branches coincide modulo a full turn. An equal-length arm folded onto its own base is a special case with infinitely many shoulder angles. Our unequal lengths avoid that ambiguity. [Modern Robotics on inverse kinematics of open chains](https://modernrobotics.northwestern.edu/nu-gm-book-resource/inverse-kinematics-of-open-chains/)

For a sequence of targets, keep both candidates until you check joint limits and collisions and compare allowable motion from the current configuration. The closest endpoint can still require an obstructed approach. Check the swept motion too. For more complicated arms a numerical solver can iteratively reduce the tip error from an initial guess. Seed it from the current configuration for continuity, check the final residual, and try other seeds when necessary. A failed iteration alone does not establish geometric impossibility. [Modern Robotics on numerical IK](https://modernrobotics.northwestern.edu/nu-gm-book-resource/6-2-numerical-inverse-kinematics-part-1-of-2/)

## Read the velocity and detect singularities

The position **Jacobian** `J(q)` has one column per joint. Column `i` differentiates the two FK coordinates with respect to joint `i`, holding the other fixed. By the chain rule, `p_dot = J(q) q_dot`. Multiplying the columns (meters per radian) by joint rates (radians per second) produces a base-frame velocity in meters per second.

For this task, `det(J) = L1 L2 sin(q2)`. When straight or fully folded, the two column directions are collinear. The tip loses its instantaneous radial motion even though the joints still turn. Close to this **singularity**, commanding a radial tip velocity can require excessive joint rates. A damped least-squares inverse trades task error for smaller rates. If you need accurate motion in the lost direction, plan a different approach and evaluate both residual and joint speeds. [Modern Robotics on singularities](https://modernrobotics.northwestern.edu/nu-gm-book-resource/5-3-singularities/)

## Experiment: prove your FK, IK, and Jacobian agree

Use Python 3 with no dependencies. Save the block as `model-arm.py` and run `python model-arm.py`. Choose 0.30 m and 0.20 m links and predict the zero and quarter-turn poses on paper first. Then find both roots for the same point and compare each analytic Jacobian column to a centered finite difference.

```python
from math import atan2, cos, dist, pi, sin, sqrt

L1, L2 = 0.30, 0.20


def fk(q1, q2):
    return (L1*cos(q1) + L2*cos(q1 + q2),
            L1*sin(q1) + L2*sin(q1 + q2))


def ik(x, y):
    c = (x*x + y*y - L1*L1 - L2*L2) / (2*L1*L2)
    tolerance = 1e-12
    if abs(c) > 1 + tolerance:
        return []
    if abs(abs(c) - 1) <= tolerance:
        c = 1.0 if c > 0 else -1.0
    s = sqrt(1 - c*c)
    return [(atan2(y, x) - atan2(L2*signed_s, L1 + L2*c),
             atan2(signed_s, c))
            for signed_s in ((s, -s) if s else (0.0,))]


def jacobian_columns(q1, q2):
    x, y = fk(q1, q2)
    return (-y, x), (-L2*sin(q1 + q2), L2*cos(q1 + q2))


assert dist(fk(0, 0), (0.50, 0)) < 1e-12
assert dist(fk(pi / 2, 0), (0, 0.50)) < 1e-12
assert len(ik(0.50, 0)) == len(ik(0.10, 0)) == 1
assert ik(0.51, 0) == ik(0.05, 0) == []
roots = ik(0.30, 0.20)
assert len(roots) == 2 and roots[0][1] > 0 > roots[1][1]
step = 1e-6  # rad
for q1, q2 in roots:
    assert dist(fk(q1, q2), (0.30, 0.20)) < 1e-12
    pairs = [(fk(q1 + step, q2), fk(q1 - step, q2)),
             (fk(q1, q2 + step), fk(q1, q2 - step))]
    for column, (plus, minus) in zip(jacobian_columns(q1, q2), pairs):
        numeric = tuple((a - b)/(2*step) for a, b in zip(plus, minus))
        assert dist(column, numeric) < 1e-8
    print(f"q = ({q1:.3f}, {q2:.3f}) rad, tip checks pass")

for angle in (pi / 2, 0.01, 0.0):
    (a, b), (c, d) = jacobian_columns(0, angle)
    print(f"q2={angle:.3f} rad, det(J)={a*d - b*c:.6f}")
```

Expect roots near `(0.000, 1.571)` and `(1.176, −1.571)` rad. The determinant falls from 0.060000 to about 0.000600 to zero. Repeat with a nonzero base-to-task transform by converting the target into the base first. If the fixture poses fail, check link units and angle zeroes before touching IK. If the analytic and numeric columns disagree, check which angle the perturbation changes and whether the derivative output is in the base frame. These checks establish consistency and simple geometric cases in Python. An arm model for commissioning also needs independently checked link dimensions, frame offsets, joint limits, and simulation or supervised dry-run validation.

## Exercises

1. At `(0.30, 0.20) m`, a simulated joint stop permits only `−2.0 ≤ q2 ≤ 0.2` rad. Which candidate remains and what check is still missing?

<details>
<summary>Solution</summary>
<p>The second solution, approximately (1.176, −1.571) rad, passes the elbow limit. Check the shoulder limit, the model's collisions, and the swept motion from the current joint state before accepting it.</p>
</details>

2. At `q = (0, 0)`, predict the tip velocity for joint rates `(0.4, −1.0) rad/s`. What does this imply for a Cartesian jog along +X at that pose?

<details>
<summary>Solution</summary>
<p>The columns are (0, 0.50) and (0, 0.20) m/rad, so the two contributions cancel and the tip velocity is (0, 0) m/s. More generally every attainable instantaneous tip velocity has x component zero at this pose. Moving along +X would also move beyond the workspace boundary. Reposition away from the boundary before requesting radial motion.</p>
</details>

## Summary

- Joint configuration specifies the mechanism. The chosen task and its workspace describe what can be commanded at the tip.
- FK composes known transforms. IK can return multiple joint states, each of which needs feasibility and path checks.
- The Jacobian maps joint rates to tip velocity. Loss of rank removes an instantaneous direction, regardless of whether FK is correct. To ask what input makes the arm move, continue with [Robot dynamics and actuation](/notes/robot-dynamics-and-actuation/).
