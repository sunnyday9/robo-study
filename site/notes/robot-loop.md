---
title: Build your first robot loop
topic: Robotics fundamentals
order: "005"
description: Build a one-axis robot in Python, then find out why sensing delay and actuator limits matter.
prerequisites: Basic Python; standard library only.
minutes: 45
---

## Start with a testable problem

Move a simulated cart from a starting position of zero to a target one meter away. The cart has a velocity limit. In one experiment it gets a biased measurement, and in another the reading is delayed. There is no ROS middleware, physics engine, or neural network. That is deliberate: if a five-line controller behaves unexpectedly, you should be able to inspect every variable that can explain it.

Our acceptance test is simple: after 40 iterations at 0.1 seconds per iteration, the **true** position must be within 0.08 m of the target. That is a criterion for this teaching fixture, not a physical robot requirement.

## Draw the system before coding it

```text
   reference [m] ─▶ controller ─▶ requested speed [m/s]
                         ▲                  │ clamp
                         │                  ▼
   measured position ◀── sensor ◀── plant integrates speed
        [m, old or noisy]           true position [m]
```

**State** is what the plant tracks; here it is true position. **Observation** is what the controller gets to know; here it is a potentially delayed and biased measurement. **Command** is what the controller asks for. **Applied input** is what the plant actually receives after the limit. In a real system every boundary can have more uncertainty, but keeping these names separate helps in any stack.

At each tick, first read the existing state through the sensor model. Next compute the command. Then step the plant. A log row that pairs the command with the position *after* moving changes the meaning of the observation. This ordering is important again in [demonstration data](/notes/lerobot-data/).

## Build the first loop

Save this as `first_cart.py`, then run `python first_cart.py`. It empties its state on each call and never interacts with hardware. The model sets velocity immediately and ignores mass, friction, and contacts; later chapters replace that assumption rather than adding unexplained complexity to the first lab.

```python
def simulate(label, gain=2.0, bias=0.0, delay_ticks=0, speed_limit=0.5):
    target, time_step, ticks = 1.0, 0.1, 40
    positions = [0.0]
    peak = positions[0]
    clipped = 0
    for tick in range(ticks):
        observed_position = positions[max(0, tick - delay_ticks)] + bias
        error = target - observed_position
        requested_speed = gain * error
        applied_speed = max(-speed_limit, min(speed_limit, requested_speed))
        clipped += requested_speed != applied_speed
        next_position = positions[-1] + applied_speed * time_step
        peak = max(peak, next_position)
        positions.append(next_position)
        if tick in (0, 10, 20, 39):
            print(f"{label:8} t={tick * time_step:3.1f}s "
                  f"obs={observed_position:5.2f} "
                  f"request={requested_speed:5.2f} applied={applied_speed:5.2f}")
    final_error = abs(target - positions[-1])
    print(f"{label:8} final={positions[-1]:.3f} m, peak={peak:.3f} m, "
          f"clipped={clipped}, pass={final_error <= 0.08}")
    return final_error, peak


baseline_error, baseline_peak = simulate("baseline")
biased_error, _ = simulate("bias", bias=0.15)
_, delayed_peak = simulate("delay", delay_ticks=8)
assert baseline_error <= 0.08
assert biased_error > 0.08
assert delayed_peak > baseline_peak
```

Check the first tick before reading the later values. The controller requests 2 m/s, the plant can apply 0.5 m/s, so the first move is 0.05 m. The ratio between position error and requested velocity has units of inverse seconds. These unit checks can catch a surprising number of mistakes.

## Predict, run, and diagnose

The baseline should pass. The biased sensor tells the controller the cart is farther along than it really is; the resulting true position tends toward 0.85 m even if measured error goes to zero. Tuning the gain cannot remove an unknown fixed bias from a controller that trusts that measurement. Before tuning, compare sensor readings against an independent reference.

For the delayed run, the controller is acting on positions up to 0.8 s old. It can keep moving toward the target after the true cart has reached it. The larger peak is the symptom; the oldest measurement used and the difference between requested and applied speed are the evidence. Do not use only the final error to judge this case: it can hide an excessive excursion.

Now change one input. Reduce the speed limit to 0.2 m/s while keeping the 4 s horizon. Even perfect commands cannot overcome the distance bound of 0.8 m. Increase the time horizon or change the design constraint before proposing another gain. Keep that distinction between “the target was not feasible” and “the controller was poorly tuned.”

## Transfer exercises

Your trace shows a requested speed of +2 m/s but position changes by only +0.05 m in one 0.1 s step. Is the integrator wrong?

<details>
<summary>Check the first-tick reasoning</summary>
<p>Not on this evidence. The applied speed is limited to +0.5 m/s, which gives +0.05 m. Log the applied speed before diagnosing integration.</p>
</details>

A teammate changes the script to log the latest position after each move as its input for that command. What future experiment does that invalidate?

<details>
<summary>Check the data contract</summary>
<p>A learner or offline evaluator could use information caused by the action to predict the same action. Preserve the actual observation used, its acquisition tick, the command, and the resulting next state separately.</p>
</details>

## Keep this experiment

Save the script, baseline output, one changed condition, and your explanation of the first wrong assumption. You now have a complete, if tiny, robotics development loop. Next, [check units and timestamps](/notes/robot-math-and-measurement/) and [change coordinate frames](/notes/coordinate-frames/) before building a more realistic model.
