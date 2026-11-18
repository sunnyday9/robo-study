---
title: PID feedback
topic: Control
order: "02"
description: Compute a discrete controller update and see why actuator limits matter.
---

## The idea

A feedback controller measures the current output and compares it with a target. Define error as `target − measurement`. A PID controller combines the current error, its accumulated history, and its rate of change. For a fixed sampling interval:

```text
integral = previous_integral + error × dt
slope    = (error − previous_error) / dt
command  = Kp × error + Ki × integral + Kd × slope
```

Initialize the previous error to the first measurement's error before taking the first derivative. A discrete derivative magnifies measurement noise; gains for this exercise are not settings for real hardware.

## Worked example

In a simulation with normalized units, let the current error be `0.2`, the previous error `0.3`, and the previous integral `0.1`. With `dt = 0.1 s`, the updated integral is `0.12` and the slope is `−1`. Gains of `Kp = 2`, `Ki = 0.5`, and `Kd = 0.1` give:

```text
2 × 0.2 + 0.5 × 0.12 + 0.1 × (−1) = 0.36
```

If the actuator accepts at most `0.3`, the applied command is `0.3`. Clipping the command alone does not stop the integral from growing. If error keeps driving the command into the limit, that accumulated error can delay recovery. This is integral windup.

## Try it

Keep the worked example's inputs and gains but set `Kd = 0`. What are the computed and applied commands?

<details>
<summary>Check your answer</summary>
<p>The computed command is 0.46 and the applied command remains 0.3. The derivative previously reduced the command because the error was falling.</p>
</details>

## Read next

- [Modern Robotics §11.4: Motion control with torque or force inputs](https://modernrobotics.northwestern.edu/nu-gm-book-resource/11-4-motion-control-with-torque-or-force-inputs-part-2-of-3/)
