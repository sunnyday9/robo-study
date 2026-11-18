---
title: "Turn robot observations into scene geometry"
topic: "Perception and estimation"
order: "042"
description: "Recover 3D points from range or depth, choose a scene representation, and measure a tabletop segmentation failure."
prerequisites: "Coordinate frames, pinhole camera projection, and sensor calibration."
minutes: 55
---

## Decide what the downstream system needs

A tabletop manipulator needs a target in meters relative to its base. A detector can identify the right object in an image while giving a poor 3D target because the bounding box includes the table. An indoor rover has a different question. It needs to know which nearby space was observed free, which space contains obstacles, and where observations are missing. Both problems begin with calibrated observations and turn them into a representation designed for a particular decision.

For each output, write down the consumed frame, acquisition time, units, meaning of missing data, and spatial tolerance. For the lab, the output is the centroid of visible target points in a base frame. The reference is the centroid of an ideal visible surface in the same frame. An object center or feasible grasp pose would require additional information about the object's shape and the hand.

## Recover 3D points, then choose a representation

In [pinhole camera projection](/notes/camera-projection/), a pixel defined a ray. For a rectified pixel `(u, v)`, form `q = ((u - cx)/fx, (v - cy)/fy, 1)`. If the sensor reports **axial depth** `Z`, the camera-frame point is `Z q`. If it reports **range** `r` along that same ray, the point is `r q / ||q||`. At horizontal normalized coordinate 0.6 and vertical coordinate zero, a 2 m ray range gives forward depth about 1.715 m. Treating it as axial depth gives 2 m, with error that grows toward the image edge. ROS REP 118 defines a canonical depth image with axial depth in float meters and an alternative raw representation in unsigned integer millimeters. Parse the actual encoding and check validity before using the value. [ROS REP 118 depth image format](https://github.com/ros-infrastructure/rep/blob/master/rep-0118.rst)

For a planar lidar in its scan frame, a range `r` at angle `a` gives `(r cos(a), r sin(a), 0)`. Enumerating the beams uses the scan's angle start and increment. If the rover moves appreciably during the scan, transform each point using its acquisition time where the pose history supports that. A depth image can have a different acquisition convention, and associating it with a color mask requires spatial alignment and appropriate timestamps. Pixel indices have meaning within their own camera and image geometry. [ROS LaserScan message](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/LaserScan.msg) · [OpenCV calibration and stereo geometry](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)

```text
Sensor origin O ----------- X .............. ?   distance along one ray
              | traversed | hit             | behind hit
                 free        occupied         unobserved

Endpoint X contributes a point to a cloud.
Origin O + the valid ray + hit X contribute evidence to an occupancy map.
```

A point cloud holds observed surface coordinates, possibly with color or descriptors. An organized cloud preserves the pixel grid, including holes. A voxel grid groups points into fixed-size 3D bins. Downsampling can control compute, but a thin feature can disappear or merge with another surface. An occupancy representation uses observations to reason about space around those surfaces. With a valid opaque hit under a simple ray model, traversed cells receive free evidence and the hit cell receives occupied evidence. The space behind it remains unknown. An invalid sample can arise from poor reflectance, lack of stereo correspondence, or other sensor-specific conditions. Decode those conditions before deciding whether a ray supplies free-space evidence. [OctoMap representation of occupied, free, and unknown space](https://octomap.github.io/)

## Pick a baseline and measure errors where they matter

<figure class="lesson-figure">
  <a href="/assets/figures/sensor-to-map.svg"><img src="/assets/figures/sensor-to-map.svg" width="640" height="305" loading="lazy" decoding="async" alt="A sensor beam supplies free evidence in cells it crosses, occupied evidence at the marked hit, and no evidence in cells beyond the hit."></a>
  <figcaption>A point cloud records the hit position. An occupancy update uses the ray as well, but space behind the return stays unobserved.</figcaption>
</figure>

**Detection** associates instances with locations such as boxes. **Semantic segmentation** assigns a category to each pixel or point. **Instance segmentation** also distinguishes individual objects within the same category. Begin with geometry when the task allows it. For a fixed tabletop, estimate or survey its plane, keep points in a height band, and group neighboring points. A learned model can distinguish objects with similar geometry, but requires labeled data and checks under the intended lighting, viewpoints, and backgrounds. A detection box can propose a region for depth processing. Inspect which pixels or points actually support the resulting target.

For masks, intersection over union (IoU) divides their overlapping area by their union. For detections, match predictions and labels under a declared overlap rule, count precision and recall, then vary the confidence threshold. For example, the COCO evaluator reports average precision over multiple IoU thresholds. Measure task-space errors in addition to image-space scores. A one-pixel depth discontinuity can pull a target estimate toward a different surface even with a high mask IoU. Track the fraction of labels yielding a valid 3D target, median and tail position error among valid targets, false positives in empty scenes, and time from acquisition to result. [COCO reference evaluator](https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/cocoeval.py)

## Lab: find a raised patch and break the depth baseline

Save the snippet as `sensing-perception.py` and run `python sensing-perception.py`. Use an 8 by 4 rectified depth image from a simulated overhead camera. The camera origin is `(0, 0, 0.80)` m in the base frame, whose z axis is up. Optical +X is base +X, optical +Y is base −Y, and optical +Z points down. All pixels share one acquisition time and a fixed transform. The true top is 0.10 m above the table. The second fixture changes only depth measurements, simulating a combination of a missing return, a mixed return near the table, and a spurious foreground return. The labels stay fixed.

```python
from math import dist, isfinite
from statistics import mean

pixels = {(u, v) for v in range(4) for u in range(8)}
target = {(3, 1), (4, 1), (3, 2), (4, 2)}
clean = {p: 0.70 if p in target else 0.80 for p in pixels}
shifted = clean | {(3, 1): float("nan"), (4, 1): 0.78, (7, 0): 0.70}


def base_point(pixel, depth_m):
    u, v = pixel
    return ((u - 3.5) * depth_m / 100,
            -(v - 1.5) * depth_m / 100,
            0.80 - depth_m)


def centroid(points):
    return tuple(mean(axis) for axis in zip(*points))


truth = centroid([base_point(p, clean[p]) for p in sorted(target)])
for name, image in [("clean", clean), ("shifted", shifted)]:
    valid = {p: base_point(p, z) for p, z in image.items()
             if isfinite(z) and z > 0}
    picked = {p for p, point in valid.items() if 0.04 <= point[2] <= 0.20}
    iou = len(picked & target) / len(picked | target)
    coverage = len(target & valid.keys()) / len(target)
    estimate = centroid([valid[p] for p in sorted(picked)]) if picked else None
    error = f"{1000 * dist(truth, estimate):.2f} mm" if estimate else "no target"
    print(f"{name}: depth coverage={coverage:.2f}, IoU={iou:.2f}, error={error}")
```

Expect perfect coverage, IoU, and zero error on the clean fixture. In the shifted fixture only three of four target pixels have valid depth. Two true pixels and one distractor pass the height band, so IoU is `2/5 = 0.40` and the centroid moves about 8 mm. The range of heights alone cannot isolate the target. Print the accepted pixel coordinates and verify the outlier before modifying the model. Lower the minimum height to 0.01 m and compare IoU and centroid error. The mixed pixel now passes, improving mask overlap while pushing the estimate downward. This is a reason to evaluate every metric used by the downstream system.

In replay, group validation examples by session or scene to avoid nearly identical adjacent frames leaking across a split. Add slices for object material, viewpoint, lighting and distance. Inspect overlay, point cloud, and target position for the same stamp. A mask shift with good geometry suggests problems in registration or segmentation. A correct mask and bad 3D position suggest checking depth scaling, reference plane, frame direction, and timing before retraining. Keep the CPU result scoped to this synthetic fixture. Evaluate the actual stack in simulation or dry run before supervised commissioning.

## Exercise: make the height baseline more selective

Use 4-neighbor pixel adjacency, where a neighbor shares a side. Which groups does the shifted fixture produce at the original threshold? What test would justify keeping only the largest group?

<details>
<summary>Check the result</summary>
<p>There is a two-pixel group at (3,2) and (4,2) and a singleton at (7,0). Keeping the pair improves IoU from 0.40 to 0.50 and gives a centroid error of 3.5 mm. Test partially occluded targets and scenes with a larger distractor. A largest-component rule assumes the desired return supports the largest connected region.</p>
</details>

## Exercise: interpret a blank obstacle image

A rover replay shows zero obstacle points on frames where a bright window fills part of its depth image. Should the map become free there? What curves would you compare across the window and interior-wall recordings?

<details>
<summary>Check the investigation</summary>
<p>Treat unusable rays as unknown unless the sensor contract gives specific evidence of free space. Compare valid-depth fraction, obstacle recall against scene geometry, and observation age in each region. A sudden loss of depth with preserved detector confidence points toward the depth input or its alignment. Compare valid ranges and ray directions before changing the map updater.</p>
</details>

## What to carry forward

- Back-project using the sensor's depth or range convention and transform at acquisition time.
- Choose a mask, point cloud, or occupancy grid based on what the consumer needs. Preserve unknown regions explicitly.
- Track 2D quality, 3D error, coverage, and latency under changed scene conditions. [Mapping and SLAM](/notes/mapping-and-slam/) turns registered observations into a persistent map.
