---
title: Mobile robot models
topic: Motion and control
order: "034"
description: Convert differential-drive wheel motion into a pose estimate and diagnose where rolling assumptions break down.
prerequisites: Coordinate frames, basic trigonometry, and Python.
minutes: 55
---

## Start from the motion the wheels allow

An indoor rover has two driven wheels on a common axle and a passive support caster. The wheels can make it roll forward, turn in place, or trace an arc. To park one body width to the left, it must change heading and roll through a maneuver. It cannot directly translate left while keeping both wheels rolling without sideways slip. A planar pose has three coordinates, `(x, y, θ)`, while this base has two independent instantaneous inputs. That velocity constraint is called **nonholonomic**. Given room to maneuver, a differential drive can still reach a pose offset to its side. [ros2_control on wheeled robot kinematics](https://control.ros.org/jazzy/doc/ros2_controllers/doc/mobile_robot_kinematics.html)

## Convert between wheels and body speed

Use the axle midpoint as the origin of the rover's kinematic body frame. Choose +X forward, +Y left, and +Z up. Positive yaw rotates counterclockwise viewed from above. The pose gives the axle midpoint and yaw in a fixed odometry frame, initially aligned with the robot. Adopt meters, seconds, radians, and wheel rotation signs under which both wheels report positive when rolling the rover forward. This sign convention is defined after accounting for how the encoders are mounted. [Coordinate frames](/notes/coordinate-frames/) · [ROS REP 103](https://github.com/ros-infrastructure/rep/blob/master/rep-0103.rst)

```text
Top view
                      +X forward
                           ^
                           |
  left contact L ----------o---------- R right contact
                 <---------+           o = axle midpoint
                  +Y left
  |<------- track width W (m) ------->|

  For a forward left arc: right wheel travels farther than left.
```

Call the track width `W`, the rolling radii `r_L, r_R`, and the signed wheel angular rates `Ω_L, Ω_R`. Rolling without slip maps each angular rate to a wheel's longitudinal speed, `v_i = r_i Ω_i`. The left contact is at body `y = +W/2` and the right at `y = −W/2`. Rotation about +Z subtracts forward speed at the left contact and adds it at the right, giving the inverse and forward maps:

```text
v_L = v − ω W/2                 v   = (v_R + v_L)/2
v_R = v + ω W/2                 ω   = (v_R − v_L)/W
Ω_i = v_i / r_i                  v_y = 0 at the axle midpoint
```

Here `v` is body forward speed in m/s and `ω` is yaw rate in rad/s. Equal wheel speeds produce straight motion. Equal and opposite speeds give an in-place turn. At `v = −0.20 m/s` and `ω = +1 rad/s` with a 0.30 m track, the two ground speeds are `−0.35` and `−0.05 m/s`. The rover reverses while yaw still increases. The signed path curvature `ω/v` changes sign if you reverse `v` while keeping `ω`; check whether an upstream planner defines a reverse arc by curvature or by yaw rate. If both wheel commands must fit speed limits, scaling both by the same positive factor preserves the arc geometry and slows progress. Clipping one wheel alone generally changes curvature.

## Integrate signed encoder travel

A wheel encoder measures rotation. For a counter with `N` counts per wheel revolution, consecutive counts `n_old` and `n_new` imply signed travel `d = 2πr (n_new − n_old)/N` under the rolling model. If the encoder is on the motor shaft, convert the documented counts and gearing to wheel revolutions first. Include any decoder multiplication when establishing what one count means. Take paired wheel measurements at consistent times, unwrap finite counters before differencing, and handle resets as explicit discontinuities. Divide travel by the measured time interval to estimate average speed. The travel itself already spans that interval, so do not multiply by time again.

With `Δs = (d_R + d_L)/2` and `Δθ = (d_R − d_L)/W`, integrate the axle midpoint in odometry coordinates. If wheel rates are constant over the interval, the midpoint traces a circular arc or a straight line. Its chord has signed length `Δs sinc(Δθ/2)` and heading `θ + Δθ/2`, with `sinc(a) = sin(a)/a` and `sinc(0) = 1`. Project that chord onto odometry X and Y, then add `Δθ` to yaw. This gives the exact constant-rate update. Taking a step at the starting heading is simpler Euler integration and can introduce turn error. For changing wheel rates, use shorter, time-aligned intervals because travel totals alone lose information about the order of turns and translations.

## Experiment: replay a synthetic encoder pair

Save the code as `model-odometry.py` and run `python model-odometry.py` with Python 3. Each run starts from the origin and represents one second of constant wheel speeds, sampled every 0.05 s. The simulator quantizes absolute encoder counts with 2048 counts per wheel revolution. In one trial the right wheel spins more than its effective advance on the floor. An independent pose computed from stipulated ground travel stands in for simulator ground truth. These are synthetic traces with a simplified slip scenario.

```python
from math import cos, dist, pi, sin

WIDTH = 0.30
METERS_PER_COUNT = 2 * pi * 0.05 / 2048
ORIGIN = (0.0, 0.0, 0.0)
SAMPLES = 20


def advance(pose, left, right):
    x, y, yaw = pose
    turn = (right - left) / WIDTH
    half_turn = turn / 2
    sinc = sin(half_turn) / half_turn if half_turn else 1.0
    chord = (left + right) / 2 * sinc
    heading = yaw + half_turn
    return x + chord*cos(heading), y + chord*sin(heading), yaw + turn


def replay(left, right):
    pose = ORIGIN
    last_left = last_right = 0
    for sample in range(1, SAMPLES + 1):
        fraction = sample / SAMPLES
        left_count = round(left * fraction / METERS_PER_COUNT)
        right_count = round(right * fraction / METERS_PER_COUNT)
        pose = advance(pose, (left_count - last_left) * METERS_PER_COUNT,
                       (right_count - last_right) * METERS_PER_COUNT)
        last_left, last_right = left_count, right_count
    return pose


fixtures = [
    ("forward", 0.30, 0.30, (0.30, 0.0, 0.0)),
    ("reverse", -0.30, -0.30, (-0.30, 0.0, 0.0)),
    ("spin", -0.15, 0.15, (0.0, 0.0, 1.0)),
    ("arc", 0.15, 0.45, (0.30*sin(1), 0.30*(1 - cos(1)), 1.0)),
]
for name, left, right, expected in fixtures:
    x, y, yaw = replay(left, right)
    assert dist((x, y), expected[:2]) < 0.002
    assert abs(yaw - expected[2]) < 0.002
    print(f"{name:7s} x={x:+.3f} m, y={y:+.3f} m, yaw={yaw:+.3f} rad")

estimate = replay(0.30, 0.30)
truth = advance(ORIGIN, 0.30, 0.24)
print(f"slip: position error={dist(estimate[:2], truth[:2]):.3f} m, "
      f"yaw error={estimate[2] - truth[2]:+.3f} rad")
```

Expect the forward run near +0.300 m on X, reverse near −0.300 m, and spin near +1.000 rad with no translation. The arc should end near `(0.252, 0.138) m`. In the slip trial, equal counts predict straight motion while the stipulated effective ground travel predicts −0.200 rad of yaw. Changing encoder resolution alone cannot resolve two physical outcomes with the same encoder readings.

Debug with straight, spin, and arc replays before relying on odometry. A consistent distance scale error in both directions suggests checking counts per revolution or wheel radius. A curved estimate during verified straight travel suggests a left/right scale mismatch or signs. A repeatable yaw gain error during spin suggests a track-width mismatch after checking both radius scales. Run the same scenarios with changed speed and simulated surface grip to distinguish a persistent calibration error from slip. Compare to independently timestamped pose or heading, and report position and yaw separately. In ROS vocabulary, `odom` is continuous but can drift, while a global localization estimate can correct the longer-term position. Jazzy's `diff_drive_controller` can compute odometry from joint feedback, or use commands when configured for open loop. The example here is a standalone replay of synthetic encoders. [ROS REP 105](https://github.com/ros-infrastructure/rep/blob/master/rep-0105.rst) · [Jazzy differential-drive controller documentation](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html)

## Compare the alternative chassis

For an **Ackermann** chassis, the inner and outer front wheels steer at different angles to follow concentric circles in the ideal model. Approximate them by a single virtual front wheel in the bicycle model. For rear-axle speed `v`, wheelbase `L`, and virtual steer angle `δ`, yaw rate is `(v/L) tan(δ)`. A conventional steering range gives a minimum turning radius and no in-place rotation. Reversing speed at the same steer angle reverses yaw rate. An **omnidirectional** chassis with suitably arranged omni wheels can command forward, lateral, and yaw velocities independently in its ideal kinematics. It can sidestep at a docking station. Wheel traction, roller contact, and motor limits still govern what it achieves. Choose the model based on the platform and docking geometry, then validate it with simulation replays and supervised commissioning where applicable. [ros2_control on omni wheels, bicycle models, and Ackermann steering](https://control.ros.org/jazzy/doc/ros2_controllers/doc/mobile_robot_kinematics.html)

## Exercises

1. A simulated rover requests `v = 0.30 m/s` and `ω = 2.0 rad/s` with `W = 0.30 m`. Each wheel is limited to `0.45 m/s` in magnitude. Find achievable wheel speeds preserving the turn radius.

<details>
<summary>Solution</summary>
<p>The inverse map gives left 0.00 and right 0.60 m/s. Multiply both by 0.75 to get 0.00 and 0.45 m/s. The body now moves at 0.225 m/s and turns at 1.50 rad/s, preserving the 0.15 m turn radius.</p>
</details>

2. Two synthetic replays report the same encoder counts. A simulator truth channel shows equal distances on a high-grip surface and unexpected rightward yaw on a low-grip surface. Which measurements should you compare before changing the wheel radius?

<details>
<summary>Solution</summary>
<p>Align wheel counts, independently measured yaw, and body path by acquisition time and check the same move at more than one speed. A radius error should affect the high-grip runs consistently too. A residual that follows grip or acceleration suggests slip. Keep the nominal calibration fixed while diagnosing, since encoder rotation alone cannot distinguish the two traces.</p>
</details>

## Summary

- The differential-drive map acts at the axle midpoint. Forward speed is the wheel speed average, and signed yaw rate comes from the difference divided by track width.
- Integrate timestamped wheel travel along a body arc and rotate that displacement into odometry coordinates.
- Compare odometry to an independent reference. Choose a chassis model that matches the maneuver, and evaluate where its rolling assumptions fail.
