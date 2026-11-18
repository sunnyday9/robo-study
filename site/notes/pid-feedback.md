---
title: PID feedback
topic: Control
order: "02"
description: Compute a discrete controller update and see why actuator limits matter.
prerequisites: Python and basic algebra. All control experiments are simulated.
minutes: 55
---

## Why a target is not a command

If your application asks a simulated joint to go to 1 radian, the physical input may be torque, not position. Applying a fixed torque for a fixed time assumes the joint has exactly the inertia, friction, and initial state you predicted. As soon as a load changes, open-loop commands no longer give the same result. Feedback measures what happened and uses the error to decide what to do next.

Our goal is to implement a measured, bounded experiment: for a toy system, compare three controllers against the same target and disturbance, then use the trace to explain the trade-offs. We are not finding gains for hardware. A real arm may already have an inner loop and limits, and treating a position interface as a torque interface is a different controller, not a different tuning.

```text
desired ──▶ error ──▶ PID law ──▶ output limits ──▶ plant
            ▲                                     │
            └──────────── subtract measurement ◀──┘
```

The controller sees error, not the full plant. The applied command can differ from its request. Log both: otherwise you may attribute slow movement to a small gain when the actuator was already at its limit.

## The idea

A feedback controller measures the current output and compares it with a target. Define error as `target − measurement`. A PID controller combines the current error, its accumulated history, and its rate of change. For a fixed sampling interval:

```text
integral = previous_integral + error × dt
slope    = (error − previous_error) / dt
command  = Kp × error + Ki × integral + Kd × slope
```

Initialize the previous error to the first measurement's error before taking the first derivative. A discrete derivative magnifies measurement noise; gains for this exercise are not settings for real hardware.

| Term | Useful intuition | What goes wrong |
| --- | --- | --- |
| P | A larger current error produces more correction. | The plant may need a persistent nonzero command, leaving a steady offset under P alone. |
| I | Store past error to supply a correction even as current error goes to zero. | The accumulated term can grow while the output is clipped and delay recovery. |
| D | Respond to the direction and speed of change. | Differencing noisy data amplifies rapid changes. A sudden target change can cause derivative kick when differentiating error. |

Discrete updates need an explicit timebase. Dropping `dt` from the integral or derivative makes the effective gain change when the loop rate changes. If a timer has jitter, measure the actual interval or design the loop so its timing is well bounded. Choose the same units for reference and measurement, write down the output limits, and define what happens on reset. In many applications, differentiating the measurement instead of the error avoids the large derivative caused solely by a setpoint jump.

## Worked example

In a simulation with normalized units, let the current error be `0.2`, the previous error `0.3`, and the previous integral `0.1`. With `dt = 0.1 s`, the updated integral is `0.12` and the slope is `−1`. Gains of `Kp = 2`, `Ki = 0.5`, and `Kd = 0.1` give:

```text
2 × 0.2 + 0.5 × 0.12 + 0.1 × (−1) = 0.36
```

If the actuator accepts at most `0.3`, the applied command is `0.3`. Clipping the command alone does not stop the integral from growing. If error keeps driving the command into the limit, that accumulated error can delay recovery. This is integral windup.

## Development walkthrough: compare controllers on the same plant

Use a normalized one-state teaching plant: `dy/dt = -y + applied - 0.15`. The negative term models a tendency to decay; 0.15 is a constant disturbance. The goal is `y = 0.5` and the command is clipped to ±0.8. Holding the goal at equilibrium requires `applied = 0.65`, inside the limit. Before tuning anything, this feasibility check tells you the controller could reach the goal.

Save the following as `compare_control.py` and run it using Python 3. It models only this plant and uses Euler integration; it does not send commands outside the process.

```python
TARGET, LIMIT, DISTURBANCE, DT = 0.5, 0.8, 0.15, 0.02


def trial(integral_gain, anti_windup):
    measurement = integral = 0.0
    saturated = 0
    peak = measurement
    for step in range(600):
        error = TARGET - measurement
        candidate = integral + error * DT
        requested = 3.0 * error + integral_gain * candidate
        presses_limit = (requested > LIMIT and error > 0) or (requested < -LIMIT and error < 0)
        if not anti_windup or not presses_limit:
            integral = candidate
        requested = 3.0 * error + integral_gain * integral
        applied = max(-LIMIT, min(LIMIT, requested))
        saturated += requested != applied
        measurement += DT * (-measurement + applied - DISTURBANCE)
        peak = max(peak, measurement)
        if step in (0, 49, 149, 599):
            print(f"t={(step + 1) * DT:5.2f} y={measurement:.3f} "
                  f"requested={requested:.3f} applied={applied:.3f}")
    print(f"final error={TARGET - measurement:.3f}, "
          f"overshoot={max(0.0, peak - TARGET):.3f}, clipped ticks={saturated}")


for name, gain, guard in (("P", 0.0, False), ("PI", 4.0, False), ("guarded PI", 4.0, True)):
    print(name)
    trial(gain, guard)
```

Predict the P-only steady state first. The initial command saturates, but when the loop reaches equilibrium near `y = 0.338`, the command is no longer limited: `0 = -y + 3(0.5-y) - 0.15`, so `y = 1.35/4`. You can now explain the residual without blaming a software bug. PI can carry the steady command in its integral state, but in this example integration also starts accumulating during saturation. The guarded variant holds the integral when the proposed update would drive farther into the limit. It can still integrate in the direction that unwinds that limit.

Compare final error, peak overshoot (the maximum amount above the target), and clipped ticks. Which metric changes and why? A controller is not automatically better because it minimizes one number. A slower approach may be appropriate if overshoot means hitting a simulated contact surface. Keep the plant, initial condition, and limit fixed when comparing controllers so you can explain the change.

| Controller | Final error (rounded) | Peak overshoot | Clipped ticks out of 600 |
| --- | ---: | ---: | ---: |
| P | 0.163 | 0.000 | 23 |
| PI | approximately 0 | 0.079 | 106 |
| Guarded PI | approximately 0 | 0.000 | 23 |

In this run, the unguarded PI controller is still commanding the limit at 1 s although the plant has already reached 0.413. At 3 s it has crossed the target. The guarded controller resumes normal integration after saturation, so it still compensates for the disturbance without the same stored error. This result depends on the chosen plant and gains; it does not prove guarded PI never overshoots.

![Position at three lab checkpoints: P settles below 0.5, PI overshoots, and guarded PI approaches 0.5 without overshoot in this run.](/assets/pid-response.svg)

The three checkpoints are evenly spaced for comparison, not to scale in time. The lines connect sampled points; the peak in the results table was measured over every simulated step and need not occur at a displayed checkpoint.

## Debug the next experiment

| Symptom | Check before tuning |
| --- | --- |
| All controllers settle far below the target | Calculate the steady command and check the applied limit. Change `LIMIT` to 0.6 and predict what happens. |
| Huge output on the first update after a target change | Inspect the derivative input, previous value, and time interval. The lab compared P and PI to isolate windup. |
| Response worsens after reducing update frequency | Check for a missing `dt`, discretization error, or feedback delays before increasing gains. |
| Command changes in the right direction but state moves the opposite way | Check actuator sign, coordinate convention, and which response you are measuring. |

If you add measurement noise later, keep the seed and noise amplitude constant. Compare the control signal as well as the tracking curve; a model can look smooth while rapidly changing its applied command. Measure first, change one thing, and repeat.

## Try it

Keep the worked example's inputs and gains but set `Kd = 0`. What are the computed and applied commands?

<details>
<summary>Check your answer</summary>
<p>The computed command is 0.46 and the applied command remains 0.3. The derivative previously reduced the command because the error was falling.</p>
</details>

## Transfer exercise: feasibility before gains

The output limit changes to ±0.6. Your colleague proposes doubling `Ki` to finally hold the target. What do you tell them?

<details>
<summary>Check the feasibility argument</summary>
<p>At the target, the toy plant needs an applied command of 0.65. No gain can overcome the 0.6 cap, and the best steady state at full positive command is 0.45. More integral gain can make the request grow without changing the applied value. Report saturation and reconsider the target, actuation limit, or plant design instead.</p>
</details>

## What to carry forward

- A setpoint states what you want; the plant determines how an applied command changes the state.
- Log requests and applied commands separately. Test actuator feasibility before attributing steady error to tuning.
- Compare controllers on the same starting conditions and address one failure mechanism at a time.

## Read next

- [Modern Robotics §11.4: Motion control with torque or force inputs](https://modernrobotics.northwestern.edu/nu-gm-book-resource/11-4-motion-control-with-torque-or-force-inputs-part-2-of-3/)
