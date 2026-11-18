---
title: Math, units, and measurements for robot software
topic: Robotics fundamentals
order: "006"
description: Convert raw measurements to physical units, distinguish numerical error from sensor error, and build a small interface test.
prerequisites: The first Python robot loop; basic algebra.
minutes: 55
---

## Why begin with measurements?

Most robot math begins at an interface. An encoder does not say “drive forward 6.3 cm”; it reports counts. A timestamp does not state whether it comes from the sensor, host, or simulator. Your first job is to turn each quantity into something the estimator and controller can interpret **and** preserve enough information to debug a bad conversion.

Our target: given three encoder samples, compute an incremental velocity, reject a broken timestamp, and explain what this calculation still cannot establish about physical motion.

## Build a dimensional model

Assume a wheel radius of 0.05 m and an encoder with 1,000 decoded counts per **wheel** revolution. If those counts are measured at a motor shaft, first convert through the gear ratio and check how the driver defines a count. For the lab:

```text
 raw ticks → difference / counts per revolution → revolutions
     → × (2π radians / revolution) → wheel angle change [rad]
     → × radius [m] → wheel travel [m]
     → / measured elapsed seconds → wheel speed [m/s]
```

For 200 counts in 0.1 s, the wheel turns one fifth of a revolution, about 1.257 rad. Ideal travel is roughly 0.0628 m and the estimated speed is 0.628 m/s. Wheel travel is not automatically world-frame displacement. A slipping wheel can report the same counts while the chassis barely moves.

Decide input/output conventions at the boundary. Keep distances in meters, rates in appropriate units, angles in radians for computations, and coordinate frame names beside vectors. [ROS REP 103](https://www.ros.org/reps/rep-0103.html) documents common ROS units and coordinate conventions, including right-handed frames. A system still needs to document its own axes and extrinsics.

## Numbers you will use again

| Concept | Robotics use | Minimum check |
| --- | --- | --- |
| Vector and norm | Displacement, velocity, residual magnitude | Subtract only after converting to a shared frame and unit |
| Dot product | Projection or alignment | A unit vector dotted with itself gives 1 |
| Matrix | Change a basis; approximate how a state or error evolves | Shapes match, and identity is a meaningful baseline |
| Derivative | Estimate speed or model a change | Difference divided by elapsed time; inspect noise and interval |
| Integration | Accumulate velocity or angular rate | Multiply by elapsed time; check drift and step-size sensitivity |
| Mean and variance | Separate persistent offset from scatter | Report sample count and conditions; variance does not encode a fixed bias |

The next chapters teach these concepts in context. You do not need to finish a separate math course before coding. If a result has unexpected units, write them next to every intermediate value. If an answer depends on angle sign, test something easy such as a 90° turn rather than a general trig example.

## Implement and check the contract

This runnable example assumes unwrapped counts and monotonically increasing acquisition timestamps on one clock. It raises an error rather than guessing when those assumptions fail.

```python
from math import isclose, tau


def wheel_speed(previous, current, radius=0.05, counts_per_rev=1000):
    previous_ns, previous_count = previous
    current_ns, current_count = current
    elapsed_s = (current_ns - previous_ns) / 1_000_000_000
    if elapsed_s <= 0:
        raise ValueError("acquisition timestamps must increase")
    if radius <= 0 or counts_per_rev <= 0:
        raise ValueError("invalid encoder calibration")
    turns = (current_count - previous_count) / counts_per_rev
    return turns * tau * radius / elapsed_s


samples = [(0, 0), (100_000_000, 200), (220_000_000, 440)]
speeds = [wheel_speed(left, right) for left, right in zip(samples, samples[1:])]
assert all(isclose(speed, 0.2 * tau * 0.05 / 0.1) for speed in speeds)
print([round(speed, 3) for speed in speeds])
try:
    wheel_speed(samples[1], (100_000_000, 400))
except ValueError as error:
    print(error)
else:
    raise AssertionError("bad timestamps were accepted")
```

Both intervals produce the same speed, about 0.628 m/s, because the second interval is 20% longer and contains 20% more counts. If the code assumes a fixed 0.1 s interval, it invents a 20% speed increase. That can look like actuator instability in a log. Reproduce the error with the exact same counts and fixed interval before touching the motor controller.

## Separate sample rate, latency, and accuracy

Sample rate tells you how often you receive distinct measurements; latency tells you how old a measurement is when you use it. A fast callback that reads an old sample is not fast sensing. For a simple one-count increment, the interpretation is around 0.000314 m of ideal wheel travel. With a 0.1 s difference, one count changes the estimated speed by roughly 0.00314 m/s. With a 0.01 s difference, that change is ten times larger. Sampling faster can improve recency while making a naive derivative noisier.

When diagnosing variation, keep acquisition timestamps and monotonic elapsed times distinct. A receipt clock can be useful for local processing latency, but subtracting two unrelated hardware clocks does not produce a valid delay. Use a documented synchronization or offset estimate. Check for counter wrap, resets, sign conventions, quantization, radius uncertainty, and slipping before treating every inconsistency as random noise.

## Exercises

The readings pass at 0.628 m/s, yet a tape-measure test shows the chassis moved less than predicted. Is the code definitely incorrect?

<details>
<summary>Separate the assumptions</summary>
<p>No. Compare wheel travel, wheel radius under load, and external chassis displacement. A sign or ratio error is possible, but slip makes an encoder model physically wrong even when its arithmetic passes.</p>
</details>

Your firmware sends a count at 80 Hz, but your subscriber reports bursts at 20 Hz. Which timestamp belongs in the difference?

<details>
<summary>Check the two timing layers</summary>
<p>Use acquisition timestamps for the sensor slope. Preserve receipt times to investigate batching, scheduling, or transport. If acquisition samples were dropped, compute the difference over the actual interval and report the gap.</p>
</details>

## What to keep

Write down one signed unit conversion, one bad sample test, and one independent reference you would use to check the physical assumption. Next, use [coordinate frames](/notes/coordinate-frames/) to turn local measurements into quantities another component can interpret.
