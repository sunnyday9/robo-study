---
title: Coordinate frames
topic: Kinematics
order: "01"
description: Express the same point in two frames, then chain transforms without mixing up their direction.
---

## The idea

A point does not move when you express it in another coordinate frame. Only its coordinates change. In this note, `T_A_B` maps coordinates **from B to A**. Its rotation describes B's axes in A, and its translation describes B's origin in A.

```text
p_A = R_A_B · p_B + t_A_B
T_A_C = T_A_B · T_B_C
```

When chaining transforms, read from right to left: a point in C becomes a point in B, then a point in A. The adjacent B subscripts match. Use column vectors throughout.

## Worked example

A sensor's origin is at `(2, 1) m` in the base frame. Its axes are rotated 90° counterclockwise relative to the base. It sees a point at `(1, 0) m` in its own frame.

1. Rotate the point: `(1, 0) → (0, 1) m`.
2. Add the sensor origin: `(0, 1) + (2, 1) = (2, 2) m` in the base frame.

To reverse the transform, subtract the origin **first**, then apply the inverse rotation. For a rotation matrix, the transpose is its inverse.

## Try it

[Turn the sensor in the browser lab](/demos/#frame-lab) to see how its local x-axis looks in the base frame.

With the same sensor pose, a point is at `(1, 1) m` in the base frame. What are its sensor coordinates?

<details>
<summary>Check your answer</summary>
<p>Subtract the sensor origin to get (−1, 0) m, then rotate clockwise by 90°. The result is (0, 1) m in the sensor frame.</p>
</details>

## Read next

- [Modern Robotics §3.3.1: Homogeneous transformation matrices](https://modernrobotics.northwestern.edu/nu-gm-book-resource/3-3-1-homogeneous-transformation-matrices/)
- [Pinhole camera projection](/notes/camera-projection/)
