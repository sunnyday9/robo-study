---
title: Trajectory generation and control
topic: Motion and control
order: "033"
description: Give a path a time law, track it with torque feedforward and feedback, and measure the effects of delay and saturation.
prerequisites: Robot dynamics and actuation, PID feedback, and basic derivatives.
minutes: 60
---

## A path says where to go

A tabletop arm moving a part between two fixtures needs a route and a schedule. A **path** `Q(s)` specifies configurations in order, where the progress variable `s` goes from 0 to 1. A **time law** `s(t)` specifies when the arm visits each configuration. Together they form the **trajectory** `q_ref(t) = Q(s(t))`. Reusing the path with a slower schedule changes actuator demands while preserving the sequence of geometric configurations. Collision checks on the nominal path and measurements of the executed trajectory answer different questions.

To derive the reference joint velocity and acceleration, apply the chain rule. Primes are derivatives with respect to progress and dots are derivatives with respect to time in seconds.

```text
q_dot_ref  = Q'(s) s_dot
q_ddot_ref = Q''(s) s_dot² + Q'(s) s_ddot
```

Doubling the duration of the same time law in normalized time halves the speed and quarters the acceleration. Smooth timing still needs smooth geometry. A sharp corner in a path at nonzero speed demands an instantaneous change in velocity. Blend the corner within the permitted region or schedule a stop there. For a straight joint-space move, choose `Q(s) = q_start + (q_end − q_start)s` and try `s = 10u³ − 15u⁴ + 6u⁵`, with `u = t/T` over duration `T`. It reaches both endpoints with zero speed and acceleration. A trapezoidal velocity profile gives constant acceleration segments and a possible cruise segment, with acceleration jumps at transitions. Check peak speed, acceleration, and required torque over the whole motion, including reversal and braking. [Modern Robotics on point-to-point time laws](https://modernrobotics.northwestern.edu/nu-gm-book-resource/9-1-and-9-2-point-to-point-trajectories-part-2-of-2/)

## Predict the torque and correct the error

For the isolated joint from [Robot dynamics and actuation](/notes/robot-dynamics-and-actuation/), the nominal torque feedforward is `J_eq × q_ddot_ref + b × q_dot_ref`. This supplies what the model predicts is needed to accelerate and overcome damping. Add feedback based on position and velocity errors to counter disturbances and starting-state errors. In the lab both errors use reference minus measurement. This proportional-derivative (PD) law uses a measured speed rather than a finite difference of the position error. If an application needs to reject persistent load, an integral term can help, provided the steady torque is feasible and the integral handles saturation. See [PID feedback](/notes/pid-feedback/) for an explicit anti-windup experiment. [Modern Robotics on motion control with torque inputs](https://modernrobotics.northwestern.edu/nu-gm-book-resource/11-4-motion-control-with-torque-or-force-inputs-part-2-of-3/)

```text
path + clock -> reference position, velocity, acceleration
                   |                         |
                   v                         v
measured state -> error -> feedback -----> sum <- feedforward model
                   ^                         |
                   |                         v
                   +----- sample <--- joint <- torque limiter
```

Read the upper route as the nominal calculation and the lower loop as correction from measurement. The controller sees a sampled state, and the joint receives the limited sum. Save both requested and applied torque. Delay can come from sensing, transport, filtering, computation, or applying the output. Log the sample's acquisition time, calculation time, and command application time where available. A controller running every 10 ms could still use measurements that are 180 ms old. With more delay, a correction can arrive after the error has changed sign. Raising gains can worsen the resulting oscillation.

## How to choose a controller

**State space** describes what the model needs to predict its future. The joint has state `[q, speed]`, control input torque, and potentially only measured position. An observer can estimate missing state from sensor history and the model. For linear dynamics the continuous form is `x_dot = A x + B u`; in a sampled controller the update can be expressed as `x_next = A_d x + B_d u` when ignoring disturbances. A coupled model can account for one command affecting several measured outputs. These are modeling choices used by multiple control methods.

| Method | When to reach for it | What to measure |
| --- | --- | --- |
| PID | A measured error on a mostly independent axis and a clear actuator interface. Feedforward can reduce the correction it needs to make. | Steady error, overshoot, noisy derivative estimates, saturation, and windup. |
| LQR | A model that is linear or valid near an operating point, with available or estimated states. The regulator chooses state feedback by balancing a quadratic state-error penalty against command effort. Tracking often uses deviations about a nominal trajectory and input. | Behavior outside the linear region, sensitivity to estimation, and the effect of limits absent from basic LQR. [MIT's LQR notes](https://underactuated.mit.edu/lqr.html) |
| MPC | A predictive model and important explicit constraints, such as a near-term joint or torque bound. Solve over a future horizon, apply its first command, and repeat from the new estimate. | Solve time against the control deadline, infeasibility handling, and how well the model predicts tracking and constraints. [MIT's MPC notes](https://underactuated.mit.edu/trajopt.html#model-predictive-control) |

## Experiment: hold model and path fixed

Save as `model-track.py` and run with Python 3. The simulated joint travels from 0 to 1 rad in 2 s, then holds for a second. The model in the controller knows inertia and damping. The plant alone sees a constant 0.06 N·m opposing torque. Compare feedforward alone, PD added, the same PD with stale measurements, and the same PD with a smaller torque cap. The 10 ms plant step and controller period coincide in this experiment.

```python
from math import sqrt

DT, MOVE, END = 0.01, 2.0, 3.0
INERTIA, DAMPING = 0.080, 0.12


def reference(time):
    u = min(1.0, max(0.0, time / MOVE))
    return (u**3 * (10 - 15*u + 6*u*u),
            30*u*u * (1-u)**2 / MOVE,
            60*u * (1-u) * (1-2*u) / MOVE**2)


def trial(name, feedback=False, delay=0, cap=0.60, load=0.06):
    history = [(0.0, 0.0)]
    squared_error = 0.0
    clipped = 0
    move_steps = round(MOVE / DT)
    for k in range(round(END / DT)):
        q, speed = history[k]
        goal, goal_speed, goal_accel = reference(k * DT)
        measured_q, measured_speed = history[max(0, k - delay)]
        requested = INERTIA * goal_accel + DAMPING * goal_speed
        if feedback:
            requested += 5.0 * (goal - measured_q)
            requested += 0.9 * (goal_speed - measured_speed)
        applied = min(cap, max(-cap, requested))
        clipped += applied != requested
        speed += DT * (applied - DAMPING * speed - load) / INERTIA
        history.append((q + DT * speed, speed))
        if k < move_steps:
            squared_error += (goal - q)**2
    rms = sqrt(squared_error / move_steps)
    final_error = 1.0 - history[-1][0]
    print(f"{name:13s} RMS={rms:.4f} rad  "
          f"final={final_error:+.4f} rad  clipped={clipped}")
    return rms, clipped


assert reference(0) == (0.0, 0.0, 0.0)
assert reference(MOVE) == (1.0, 0.0, 0.0)
nominal, _ = trial("nominal", load=0.0)
feedforward, _ = trial("feedforward")
tracked, _ = trial("with PD", feedback=True)
delayed, _ = trial("PD delayed", feedback=True, delay=18)
restricted, clips = trial("PD capped", feedback=True, cap=0.12)
assert nominal < tracked < feedforward
assert delayed > tracked and restricted > tracked and clips > 0
```

RMS is the root mean square of position error over the move, and final error compares the joint to the held goal at 3 s. The nominal trial checks the ideal feedforward calculation with no disturbance. Discretization still yields a small residual. The immediate PD loop reduces the error under load and leaves a small steady offset. At rest its proportional term must provide the missing 0.06 N·m, so the predicted steady error is `0.06/5 = 0.012 rad`. Delayed feedback compares the current reference with an older state, which can produce large corrections while the arm is already moving. With the smaller cap, the same controller spends more time requesting torque the simulated actuator cannot deliver.

When diagnosing a larger system, first replay a nominal run, then perturb the load, timing, and caps individually. Plot reference, measured position and speed, and request versus applied torque on a shared time axis. Preserve signal timestamps to diagnose phase lag. Sweep the delay and track RMS, peak error, and clipping together. For docking or touching a fixture, include terminal speed and clearance metrics too. Passing the free-joint simulation verifies tracking for these inputs and assumptions. A physical interface needs its own dry-run checks and supervised commissioning with approved limits.

## Exercises

1. A replay exceeds the speed bound by a factor of 1.4 and the acceleration bound by a factor of 2.25. What minimum duration multiplier addresses both for the same normalized time law? What should be checked next?

<details>
<summary>Solution</summary>
<p>The speed condition requires 1.4 or more, and acceleration requires the square root of 2.25, or 1.5 or more. Choose at least 1.5 and recompute torque, including load and gravity if present. Those terms can remain at low speed. Check executed tracking and clearance as well.</p>
</details>

2. The replay shows a regular 10 ms control period, but tracking degrades and the requested and applied torques mostly agree. How would you distinguish stale feedback from a change in stiffness or load?

<details>
<summary>Solution</summary>
<p>Compare acquisition time to the time at which the state is consumed. Replay the same plant, trajectory, and controller first with fresh measurements and then with the measured delay. If changing delay reproduces the symptom, inspect the source of the delay. If timing is sound, compare an unloaded trial with a controlled load change and inspect position and speed residuals.</p>
</details>

## Summary

- A time law gives a geometric path speed and acceleration. Check feasibility across the move and at its boundaries.
- Feedforward supplies nominal effort. Feedback corrects measured error within the actuator's limits and the loop's timing budget.
- Test the nominal loop, then change one assumption at a time. Choose a controller using the model, signals, constraints, and deadlines the system actually has.
