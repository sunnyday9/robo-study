---
title: Choose a simulator and validate the model
topic: Simulation
order: "080"
description: Separate physics, sensing, and middleware concerns, then choose the cheapest environment that can answer your engineering question.
prerequisites: Robot models, feedback, and the basics of ROS 2.
minutes: 55
---

## Start from a claim, not a simulator

Suppose your indoor rover sometimes misses a turn. You could spend a day reproducing the room in a photorealistic engine, but if a controller uses degrees instead of radians, a unit test would give a better answer. Conversely, a point in a grid cannot tell you whether a calibrated depth camera sees a reflective wall. Use the least complicated model that contains the failure mechanism you want to test.

| Question | Starting environment | What it leaves out |
| --- | --- | --- |
| Can I transform points, find a route, or detect a deadline miss? | CPU math fixture, trace replay, grid, or toy integrator | Contact, actuator dynamics, and sensor realism |
| Can my ROS 2 rover stack consume virtual odometry and publish appropriate control? | Gazebo paired with ROS 2; Jazzy and Harmonic are a documented pairing | Real network, motor, calibration, and wheel slip behavior |
| Does a policy improve over a physics baseline in controlled repeated trials? | A matching environment such as PushT, or a MuJoCo model for a task you explicitly implement | Deployment driver, timing, and hardware differences |
| Does my particular camera/RTX pipeline produce images and ROS 2 metadata from a scene? | Isaac Sim with the supported renderer and bridge | Actual lens, clocks, materials, transport, and lighting unless explicitly modeled |

These are starting points, not interchangeable backends. [Gazebo's ROS pairing table](https://gazebosim.org/docs/harmonic/ros_installation/) and [MuJoCo's simulation documentation](https://mujoco.readthedocs.io/en/stable/programming/simulation.html) describe different interfaces. [Isaac Sim](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/requirements.html) has a hardware and release contract. [LeRobot](/notes/robot-learning-methods/) consumes data or a compatible environment; it is not another physics engine.

## Understand four simulation clocks

```text
 physics step ──▶ scene state ──▶ sensor acquisition ──▶ observation
       ▲                                   │               │
       │                    render/update cadence          ▼
       └── hold action over steps ◀──── controller decision

 simulated time identifies a state; elapsed wall time measures execution cost
```

One app update can advance zero, one, or several physics steps. Rendering may be slower than physics. Control may sample at yet another interval. Treat per-step integration, control cadence, virtual acquisition time, and elapsed execution time as explicit inputs. Headless mode removes a window; it does not imply that rendering is omitted. Consumers may operate slower than their producers even when configured rates match.

Record a manifest with simulator release, scene revision, model units, solver parameters, physics step, observation cadence, control period, and reset seeds. When comparing policies, keep the evaluation environment and same initial conditions available. When comparing engine settings, keep the control rate and scenario fixed or explicitly measure their interaction.

## Lab: test a numerical assumption before installing anything

An object starts at rest with constant acceleration 1 m/s². After 1 s its exact position is 0.5 m and its velocity is 1 m/s. A simple discrete integrator gives a different result depending on its step and update order. Save this as `step_check.py`:

```python
from math import isclose


def integrate(steps, velocity_first):
    position, velocity = 0.0, 0.0
    dt = 1.0 / steps
    for _ in range(steps):
        if velocity_first:
            velocity += dt
            position += velocity * dt
        else:
            position += velocity * dt
            velocity += dt
    return position, velocity


for steps in (10, 20, 40):
    explicit, velocity = integrate(steps, False)
    semi_implicit, _ = integrate(steps, True)
    assert isclose(velocity, 1.0)
    print(f"{steps:2}: {explicit:.4f}  {semi_implicit:.4f}  exact 0.5000")
```

Predict before running: the position-first version uses the older, smaller velocity, so it underestimates travel; velocity-first overestimates it. At 10 steps expect 0.45 and 0.55 m. Halving the step halves the error in this particular constant-acceleration example. It does not establish the convergence rate of a full rigid-body contact model. A contact may appear or disappear across discretizations.

Extend this method to a chosen simulator. Start with a free-moving body or a known joint offset; compare with a hand calculation. Then add contact, friction, and sensor noise one at a time. If you change the physics rate, preserve the controller period in seconds. For example, a 20 Hz controller consumes one command every three steps at 60 physics Hz and every five steps at 100 physics Hz. Updating every third step in both experiments changes two variables, not one.

## Define what is transferable

Use separate parameter sets for calibration and evaluation; a model fitted to one recorded maneuver may not predict a new load or surface. Change plausible mass, friction, or sensor error ranges and report which outcomes change. Randomization exposes sensitivity; it does not prove that the sampled distribution describes reality. Keep failures and note any unsupported asset, missing dynamics, or simulator convenience you rely on.

If a capability relies on virtual measurements unavailable on hardware—for example, exact global pose or direct access to contact normals—label it an oracle baseline. A policy that consumes it is not a candidate for deployment until a real measurement path exists and is evaluated.

## Exercises

You halve the physics step and see a better grasp. Your policy still executes one command every four steps. What should you do next?

<details>
<summary>Check the experiment design</summary>
<p>You changed both the solver step and the simulated duration of each command. Adjust the number of steps per decision to restore the original control period, keep reset and initial contacts the same, and compare again.</p>
</details>

In a simulator, 60 RGB frames represent one simulated second but take four seconds to render. Which number matters to a dataset exporter and which matters to a deployment budget?

<details>
<summary>Check the time domains</summary>
<p>The timestamps and spacing in simulated time define the dataset sample sequence. Fifteen frames per wall second describes run throughput. Neither proves a real sensor or policy meets its end-to-end deadline.</p>
</details>

## What to carry forward

Make the model a hypothesis with acceptance criteria. Test inexpensive invariants first, then move to the [Isaac environment lab](/notes/isaac-environment/) or use a ROS-focused simulator when those interfaces are the reason for the test.
