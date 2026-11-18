---
title: Pinhole camera projection
topic: Perception
order: "03"
description: Turn a point in the camera frame into a pixel and understand what depth information is lost.
---

## The idea

In a camera frame with `Z` pointing forward, `X` right, and `Y` down, an ideal pinhole camera projects a point in front of the camera (`Z > 0`) by dividing by depth and applying its intrinsics:

```text
u = fx × (X / Z) + cx
v = fy × (Y / Z) + cy
```

`fx` and `fy` are focal lengths expressed in pixels. `(cx, cy)` is the principal point. Intrinsics describe the camera's imaging geometry; extrinsics carry coordinates between the camera and another frame. Lens distortion is not part of this ideal model.

## Worked example

Take `(X, Y, Z) = (0.1, −0.05, 1.0) m` in the camera frame, with `fx = fy = 600 px` and `(cx, cy) = (320, 240) px`. The point appears at `(380, 210) px`: right of the principal point and above it.

Doubling all three coordinates leaves both ratios unchanged. A single pixel identifies a ray, not a unique depth.

## Try it

Keep `X` and `Y` unchanged but double only `Z`. Where does the point land?

<details>
<summary>Check your answer</summary>
<p>At (350, 225) px. The displacement from the principal point halves in both directions.</p>
</details>

## Read next

- [OpenCV: Camera calibration and 3D reconstruction](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)
- [Coordinate frames](/notes/coordinate-frames/)
