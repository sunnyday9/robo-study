---
title: Coordinate frames
topic: Kinematics
order: "010"
description: Express the same point in two frames, then chain transforms without mixing up their direction.
prerequisites: Vectors and a little trigonometry. No robotics runtime.
minutes: 40
---

## Why this problem exists

Imagine a camera reports a block one meter straight ahead. A motion planner cannot act on “ahead” unless it knows ahead of what. The camera may be turned relative to the robot, and the robot may move after the image arrives. The task is not to make all components use the same coordinate system internally. It is to define a reliable conversion at the interface between sensing and planning.

Start with three questions before touching a library: **Where is the origin? Which way do the positive axes point? At what time is this description valid?** An unexplained tuple such as `[1, 0, 0]` answers none of those. A stamped pose with a source frame and known units is actionable; an unlabelled tuple is only guesswork.

By the end, you should be able to predict a transform on paper, implement and test it in Python, and recognize a reversed transform from its symptoms. The geometry here is planar so you can see the failure. The interface discipline also applies to three-dimensional [ROS 2 transforms](/notes/ros2-frames-and-time/).

## The idea

A point does not move when you express it in another coordinate frame. Only its coordinates change. In this note, `T_A_B` maps coordinates **from B to A**. Its rotation describes B's axes in A, and its translation describes B's origin in A.

```text
p_A = R_A_B · p_B + t_A_B
T_A_C = T_A_B · T_B_C
```

When chaining transforms, read from right to left: a point in C becomes a point in B, then a point in A. The adjacent B subscripts match. Use column vectors throughout.

```text
point in C ── T_B_C ──▶ point in B ── T_A_B ──▶ point in A
        tool frame             wrist frame            base frame
```

The columns of a rotation matrix are the source frame's basis vectors expressed in the target frame. For a 90° counterclockwise rotation, source +X maps to target +Y and source +Y maps to target −X. That immediately determines both columns. The translation tells you where the **source origin** goes, so it is already expressed in the target. Rotating the translation again would change which frame it belongs to.

In 3D, a rigid transform is commonly packaged as a 4×4 homogeneous matrix with `R` and `t` above a final row `[0, 0, 0, 1]`. A point has a final coordinate of 1; a direction vector has a final coordinate of 0. That is why translating the sensor moves its origin but does not change which way its axes point. The compact matrix form is convenient for composition; it is not a license to drop frame labels.

## Worked example

A sensor's origin is at `(2, 1) m` in the base frame. Its axes are rotated 90° counterclockwise relative to the base. It sees a point at `(1, 0) m` in its own frame.

1. Rotate the point: `(1, 0) → (0, 1) m`.
2. Add the sensor origin: `(0, 1) + (2, 1) = (2, 2) m` in the base frame.

To reverse the transform, subtract the origin **first**, then apply the inverse rotation. For a rotation matrix, the transpose is its inverse.

## Development walkthrough

Start with a pure function rather than ROS, a matrix package, or a camera. The following script uses the same convention as the drawing in the [browser lab](/demos/#frame-lab). Save and run it with Python 3. The return values are in meters; angles entering the math functions are in radians.

```python
from math import cos, isclose, radians, sin


def transform_point(point_source, origin_in_target, angle_deg):
    angle = radians(angle_deg)
    source_x, source_y = point_source
    offset_x, offset_y = origin_in_target
    return (
        cos(angle) * source_x - sin(angle) * source_y + offset_x,
        sin(angle) * source_x + cos(angle) * source_y + offset_y,
    )


def inverse_point(point_target, origin_in_target, angle_deg):
    relative = tuple(value - origin for value, origin in zip(point_target, origin_in_target))
    return transform_point(relative, (0.0, 0.0), -angle_deg)


def close(actual, expected):
    return all(isclose(left, right, abs_tol=1e-9) for left, right in zip(actual, expected))


origin = (2.0, 1.0)
assert close(transform_point((0.0, 0.0), origin, 90), origin)
assert close(transform_point((1.0, 0.0), origin, 90), (2.0, 2.0))
assert close(transform_point((0.0, 1.0), origin, 90), (1.0, 1.0))
assert close(inverse_point((2.0, 2.0), origin, 90), (1.0, 0.0))
print("OK: origin, both basis directions, and inverse")
```

Why these checks? The origin detects translation or operation-order errors without depending on rotation. The two basis directions expose transposes, swapped axes, and a reflected frame. The inverse checks that two boundaries compose back to the same point. A round-trip alone is weak: swapping both implementations to an incorrect but mutually inverse convention would still pass it.

Now vary one input. Change the forward and inverse calls to −90° and predict the new basis results before changing the expected values. At −90°, +X lands at `(2, 0)`, and +Y lands at `(3, 1)`. If the origin assertion passes but both axis results are opposite the prediction, examine the angle sign or transform direction. If all three are displaced by the same amount, inspect translation and units first.

When porting this code, compare the same four checks before connecting a real sensor. For a moving sensor, add a second fixture: place it at two distinct poses and prove you select the pose at acquisition time. A pose that is geometrically correct at the wrong instant can produce the same apparent offset as a calibration error. Compare runs with the robot stationary and moving to separate the hypotheses.

## Try it

[Turn the sensor in the browser lab](/demos/#frame-lab) to see how its local x-axis looks in the base frame.

With the same sensor pose, a point is at `(1, 1) m` in the base frame. What are its sensor coordinates?

<details>
<summary>Check your answer</summary>
<p>Subtract the sensor origin to get (−1, 0) m, then rotate clockwise by 90°. The result is (0, 1) m in the sensor frame.</p>
</details>

## Transfer exercise: read a transform chain

The wrist origin is at `(2, 1)` in base coordinates and rotated +90°. The tool origin is one meter along wrist +X and its axes are parallel to the wrist's. What is the tool origin in the base frame? Why can't you add `(1, 0)` directly to `(2, 1)`?

<details>
<summary>Check the chain</summary>
<p>Rotate the wrist-frame offset to (0, 1) in the base frame before adding it. The result is (2, 2). Adding the raw offsets treats the two component vectors as if they were expressed in the same basis.</p>
</details>

## What to carry forward

- Name transforms by target and source, and write the chain starting at the data.
- A translation acts on a point but not on a direction. An inverse reverses both the rotation and the order of operations.
- Verify origin, axes, and time individually. Attach the original frame ID and timestamp to observations so the next component can make the same checks.

## Read next

- [Modern Robotics §3.3.1: Homogeneous transformation matrices](https://modernrobotics.northwestern.edu/nu-gm-book-resource/3-3-1-homogeneous-transformation-matrices/)
- [Pinhole camera projection](/notes/camera-projection/)
