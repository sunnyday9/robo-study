---
title: "Choose and calibrate robot sensors"
topic: "Perception and estimation"
order: "041"
description: "Turn sensor specifications into error budgets, then separate a gyro bias from a timestamp offset in a CPU lab."
prerequisites: "Basic Python, coordinate frames, and pinhole camera projection."
minutes: 50
---

## Start with the decisions the rover has to make

A differential-drive rover needs to estimate how far it rolled, how much it turned, and what occupies its intended path. On a slick floor the wheels can turn without moving the base. A gyro still measures rotation, but its small rate offset accumulates into yaw error. A lidar can observe the room, but a planar scan can pass above a low obstacle or below a shelf. Choose complementary measurements by writing down what each sensor directly observes and where that observation breaks down.

Suppose a simulated rover moves at 0.5 m/s and turns at 1 rad/s. A 40 ms timing error corresponds to 2 cm of base translation and 0.04 rad of rotation. At a target distance of 2 m that rotation alone displaces the reconstructed point by about 8 cm sideways. This gives you a way to translate a latency or synchronization budget into a spatial budget. Use the worst relevant speed, range, and measurement age for the intended task. An average frame rate cannot tell you the age of an individual observation.

## Read the specs as measurement limits

| Sensor | What to check in a spec or driver | What to measure in a replay or fixture |
| --- | --- | --- |
| Wheel encoders | Decoded counts per output revolution, gear ratio if measured at the motor, sample cadence, counter width and sign | Distance per count, left/right asymmetry, repeated straight runs and turns, counter wrap, sensitivity to slip |
| IMU | Gyro range, noise density and bandwidth, drift with temperature, sample cadence and axis conventions | Stationary bias and scatter after warm-up, clipping, axis signs during known rotations, stability across sessions |
| Planar lidar | Angular coverage and increment, usable min/max range, range precision, scan duration, invalid-return conventions | Missed returns by material and angle, blind sectors, scan skew during turns |
| Camera | Resolution, field of view, exposure time, rolling or global shutter, frame rate and timestamp semantics | Blur, dropped frames, reprojection residuals at edges, and depth validity if a depth stream exists |

For a 0.04 m wheel radius and 2048 **decoded counts at the wheel** per revolution, a count corresponds to about 0.123 mm along the wheel circumference. That is quantization under ideal rolling. Tire compression, an incorrect radius, and slip can produce much larger travel errors. For lidar, adjacent beams separated by 0.5° are about 17 mm apart at 2 m. A narrow feature may fall between them even with excellent range precision. For an ideal camera with focal scale 600 px, a 20 mm object at 2 m spans about 6 px near the optical axis. Check the apparent size at the input resolution of the detector as well as at sensor resolution.

Assign names and units at the interface. A ROS-style `base_link` typically uses x forward, y left, z up. A camera optical frame uses x right, y down, z forward. A ROS `Imu` message expresses angular velocity in rad/s and acceleration in m/s². Its all-zero covariance denotes unknown covariance. Treat units, raw-versus-filtered data, and the timestamp's meaning as part of the driver contract. [ROS REP 103](https://github.com/ros-infrastructure/rep/blob/master/rep-0103.rst) · [ROS Jazzy IMU message](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/Imu.msg)

## Separate geometry, timing, and repeatability

```text
Raw samples + acquisition timestamps
  |
  +-- Intrinsics: decode the sample in sensor coordinates
  |               e.g. pixels to rays, counts to wheel angle
  +-- Extrinsics: express sensor geometry in the base frame
  |               p_base = R_base_sensor p_sensor + t_base_sensor
  +-- Time:       place the sample on the estimator's clock
                  then look up moving transforms at that time
```

Each correction answers a different question about the same observation. **Intrinsic** calibration identifies internal parameters such as focal scales and lens distortion, or an IMU axis scale and offset. With a known planar camera target, spread observations across the image and vary distance and orientation. Fit on one set of views, then inspect held-out pixel residuals by location. **Extrinsic** calibration estimates a rigid transform between frames. A camera calibration can estimate the target-to-camera transform for each image. A camera-to-base mount still needs an independent geometric relationship to the base. Log the transform direction and verify it with a hand-computable point. [OpenCV camera calibration model and API](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)

For **time** calibration, establish which clock stamped the acquisition and how it maps to the clock of your reference. Reception time includes transport and scheduling delays. A constant offset can align stable clocks over a short session. Plot residuals against elapsed time to look for clock drift, and against motion to look for acquisition or timestamp errors. Check whether samples are acquired together. The ROS `LaserScan` stamp refers to the first ray, and `time_increment` gives the interval between rays. Kalibr's documented camera–IMU workflow estimates spatial and temporal calibration from recorded data. [ROS LaserScan message](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/LaserScan.msg) · [Kalibr camera–IMU calibration](https://github.com/ethz-asl/kalibr/wiki/camera-imu-calibration)

For a measurement with trusted reference `r`, compute residuals `e = measured - r`. The mean estimates bias under those conditions. The sample variance `sum((e - mean(e))²)/(n - 1)` measures scatter around that mean, with squared measurement units. A tight cluster can be far from the reference. Check repeatability across samples, then redo the measurement after a power cycle or remount to see how well the calibration transfers. Large changes with temperature suggest recording temperature alongside readings. Reference uncertainty sets a floor on what you can infer.

## Lab: distinguish gyro bias from a late timestamp

Save this as `sensing-calibration.py` and run `python sensing-calibration.py`. The synthetic gyro stamps samples 40 ms late. A reference supplies the yaw rate at any time in the fixture. The first 100 samples are stationary, then the simulated rover varies its turn rate. Fit candidate offsets in 1 ms steps on one moving segment and score on a later segment. The correction convention is `acquisition = stamp - offset`.

```python
from math import sin, sqrt
from random import Random
from statistics import mean, stdev

rng = Random(41)


def reference(t):  # rad/s, with t in seconds on the reference clock
    s = max(0.0, t - 1.0)
    return 0.60 * sin(3.0 * s) + 0.25 * sin(7.0 * s)


samples = []
for i in range(600):
    t = i * 0.01
    rate = reference(t) + 0.035 + rng.gauss(0, 0.004)
    samples.append((t + 0.040, rate))

stationary = [rate for _, rate in samples[:100]]
bias = mean(stationary)
fit = samples[110:400]
holdout = samples[410:]


def rmse(rows, offset_ms, bias_rad_s):
    return sqrt(mean(
        (rate - bias_rad_s - reference(stamp - offset_ms / 1000)) ** 2
        for stamp, rate in rows
    ))


offset_ms = min(range(-80, 81), key=lambda ms: rmse(fit, ms, bias))
print(f"rest bias {bias:+.4f}, scatter {stdev(stationary):.4f} rad/s")
print(f"fitted offset {offset_ms:+d} ms")
for label, ms, correction in [
    ("raw", 0, 0), ("bias only", 0, bias), ("bias + time", offset_ms, bias)
]:
    print(f"{label}: holdout RMSE {rmse(holdout, ms, correction):.4f} rad/s")
```

Expect a bias near +0.035 rad/s, scatter near 0.004 rad/s, and a positive offset near +40 ms. Bias correction centers the errors. Timing correction should bring holdout RMSE near the injected scatter. Change `stamp - offset_ms / 1000` to addition in the scorer while keeping the stated convention in mind. A nearly identical score with a negative fitted value shows why an offset needs a documented sign and clock pair, even when the fit is excellent.

On a recording, use independently stamped reference samples and interpolate within their valid span. Plot the bias-corrected residual against the reference rate's slope. A small late stamp at increasing rate makes the uncorrected residual negative. If the best offset differs sharply by time window, investigate clock drift or buffering before increasing the fit's flexibility. Keep the fitted values, clock pairing, device configuration, calibration data identifier, and holdout metrics together. Start in simulation or on recorded data. Any hardware confirmation belongs in a supervised commissioning procedure.

## Exercise: choose a complementary measurement

A simulated rover keeps losing its heading on a featureless straight corridor. Its IMU has good short-term repeatability, and a planar lidar mainly sees the two side walls. Which drift can the walls help correct? How would you test wheel scale independently?

<details>
<summary>Check your reasoning</summary>
<p>The wall directions can constrain yaw and their ranges can constrain cross-track position. Ideal parallel walls without ends or landmarks provide no along-corridor position cue. Compare signed encoder travel with independent surveyed displacement or simulator truth over several straight traversals, in both directions and under representative traction. Keep validation runs separate from the fit.</p>
</details>

## Exercise: make the offset unidentifiable

Change the reference function to return a constant 0.0. Why can the lab still estimate bias? What should your calibration tool report about the offset?

<details>
<summary>Check the result</summary>
<p>Stationary truth is zero, so the observed mean still estimates bias. Every offset gives the same reference value and loss. The minimum search returns its first tied candidate. The data provide no timing information. Report an unidentifiable offset and collect a segment with changing rate. Even a single periodic motion can produce several plausible offsets separated by its period.</p>
</details>

## What to carry forward

- Budget sensor errors against the robot's task, including running conditions, sample age, and coverage.
- Keep intrinsic, extrinsic, and clock calibration explicit. Validate bias, scatter, and repeatability on independent views or sessions.
- Calibrated geometry and timestamps support [robot perception](/notes/robot-perception/) and [state estimation](/notes/state-estimation/). Revisit [coordinate frames](/notes/coordinate-frames/) and [pinhole camera projection](/notes/camera-projection/) for transform and image conventions.
