---
title: Pinhole camera projection
topic: Perception
order: "040"
description: Turn a point in the camera frame into a pixel and understand what depth information is lost.
prerequisites: Coordinate frames and basic algebra. The lab uses standard Python.
minutes: 40
---

## Why project a known point?

Suppose a detector puts a bounding box around a cube and the robot knows where the cube should be in its base frame. A first diagnostic is to project a known 3D point into the image and compare it to an observed pixel. This cheap check can separate an incorrect camera pose from a model error before paying for a training run.

A camera produces two measurements for a point that lives in three dimensions. Projection answers **which pixel should see this point if it is visible?** It does not answer **where is this pixel in the world?** without another measurement or assumption. Also, a projected point is not necessarily visible: it can be occluded or outside the usable image despite having positive depth.

```text
Point in scene   ── extrinsics ──▶  Point in camera frame
                                     │ divide by forward depth
                                     ▼
Pixel (u, v)     ◀── intrinsics ──  Normalized ray (X/Z, Y/Z)
```

Your observable result for this lecture is a handful of projected points with predictable directions, plus a table of pixel residuals you can use to propose a next diagnostic.

## The idea

In a camera frame with `Z` pointing forward, `X` right, and `Y` down, an ideal pinhole camera projects a point in front of the camera (`Z > 0`) by dividing by depth and applying its intrinsics:

```text
u = fx × (X / Z) + cx
v = fy × (Y / Z) + cy
```

`fx` and `fy` are focal lengths expressed in pixels. `(cx, cy)` is the principal point. Intrinsics describe the camera's imaging geometry; extrinsics carry coordinates between the camera and another frame. Lens distortion is not part of this ideal model.

Derive the division by imagining a plane one unit in front of the camera. A ray from the origin through `(X, Y, Z)` hits that plane at `(X/Z, Y/Z, 1)`. Multiplying by focal length scales the normalized coordinates to pixels; adding the principal point puts the optical axis at its measured place in the image. A camera may have different focal scales in x and y. Pixel Y is down in this convention: a negative camera Y moves to a smaller pixel row.

Many robots use a body frame whose +X is forward. That is not the same as the optical frame in the equations above. If a pose is given as **camera in world**, it describes the camera axes and origin in the world. Projecting a world point needs the **world-to-camera** transform, the inverse of that pose. Check the camera-frame coordinates before debugging the pixel math.

## Worked example

Take `(X, Y, Z) = (0.1, −0.05, 1.0) m` in the camera frame, with `fx = fy = 600 px` and `(cx, cy) = (320, 240) px`. The point appears at `(380, 210) px`: right of the principal point and above it.

Doubling all three coordinates leaves both ratios unchanged. A single pixel identifies a ray, not a unique depth.

![A side view shows two points at different depths on the same viewing ray crossing the virtual image plane at one pixel.](/assets/camera-projection.svg)

The diagram shows only the horizontal slice. The same reasoning applies vertically: keeping both ratios fixed leaves the same 2D pixel.

## Development walkthrough: make a small projection oracle

Save the following as `project_points.py` and run it with Python 3. It checks the model at the optical axis, to the right, above center, and at a farther depth. Keep this fixture independent of your full camera pipeline. It is for ideal or rectified images, not raw distortions.

```python
from math import isclose


def project(point_camera, intrinsics):
    camera_x, camera_y, depth = point_camera
    focal_x, focal_y, center_x, center_y = intrinsics
    if depth <= 0:
        raise ValueError("point is not in front of the camera")
    return (
        focal_x * camera_x / depth + center_x,
        focal_y * camera_y / depth + center_y,
    )


intrinsics = (600, 600, 320, 240)
fixtures = [
    ((0.0, 0.0, 1.0), (320, 240)),
    ((0.1, 0.0, 1.0), (380, 240)),
    ((0.0, -0.05, 1.0), (320, 210)),
    ((0.1, -0.05, 2.0), (350, 225)),
]
for point, expected in fixtures:
    uv = project(point, intrinsics)
    assert all(isclose(actual, reference) for actual, reference in zip(uv, expected)), (point, uv)
    print(point, uv)
```

1. **Implement the simplest model.** Use meters consistently for the three coordinates. The ratios are unitless; mixing millimeters in depth with meters in x breaks them.
2. **Validate the boundary.** Positive depth allows a projection; explicit image bounds tell you if it lies in the image. A crop, resize, or rectification step changes which intrinsics describe a given pixel array. For resize with scales `sx` and `sy`, scale the corresponding focal length and principal-point coordinate. For a crop, subtract the crop's origin from the principal point.
3. **Try a deliberate error.** Flip the sign of `camera_y` just before projection. The optical axis and horizontal case still pass, but the above-center point goes below center. A single center point could not detect this convention bug.
4. **Use multiple scene points.** Compare observed minus predicted pixel positions across the image, at more than one depth. Keep raw and rectified coordinates separate.

| Illustrative residual pattern | Hypothesis to test, not a diagnosis |
| --- | --- |
| Nearly the same pixel shift everywhere | Crop offset or principal point changed. Verify image geometry first. |
| Residual grows toward the edges | Check scale, focal-length change, or distortion model; test against a wide-spread calibration target. |
| Correct when still, wrong in motion | Compare the image acquisition stamp and the transform selected for projection. |
| Repeatedly negative depth | Check transform direction and optical axes before tuning calibration. |

For an actual calibration, use a known target sampled across a range of views, fit intrinsics and distortion, then examine residuals on different frames. Lower training residual can also come from a richer parameterization, so keep a validation view set separate. The [OpenCV camera model](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html) specifies the convention used here.

## Try it

Keep `X` and `Y` unchanged but double only `Z`. Where does the point land?

<details>
<summary>Check your answer</summary>
<p>At (350, 225) px. The displacement from the principal point halves in both directions.</p>
</details>

## Transfer exercise: catch a resize bug

A 640×480 rectified image is resized to 320×240, without a crop. The original camera projects a point to `(380, 210)`. What does a correct resized overlay show? What else must you update?

<details>
<summary>Check the resize reasoning</summary>
<p>The overlay is at (190, 105). Scale both focal lengths and both principal-point coordinates by 0.5. If you project with the original intrinsics onto the resized image, the output is in the wrong pixel coordinate system; the original calibration is not necessarily bad.</p>
</details>

## What to carry forward

- Check extrinsics and optical axes before inspecting the pixel math. Use the matching intrinsics for the image actually consumed.
- Projection discards depth. To back-project a pixel to a 3D point, supply depth, intersect the ray with known geometry, or use a second view with a known baseline.
- Predict and inspect residual patterns before changing the detector. Use points at multiple positions, depths, and acquisition times.

## Read next

- [OpenCV: Camera calibration and 3D reconstruction](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)
- [Coordinate frames](/notes/coordinate-frames/)
