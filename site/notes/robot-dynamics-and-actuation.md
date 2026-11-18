---
title: Robot dynamics and actuation
topic: Motion and control
order: "031"
description: Turn actuator commands and external loads into predicted joint motion, then test which limits and forces explain the result.
prerequisites: Robot kinematics, basic algebra, and Python.
minutes: 55
---

## From geometry to motion under load

A tabletop arm can reach the same dot with an empty gripper or a heavy payload. [Kinematics](/notes/robot-kinematics/) gives the same tip pose for the same joint angles. The loaded arm may accelerate more slowly, require more torque, or fail to hold a pose. **Dynamics** connects what is applied to what accelerates. Start with a single joint rotating a horizontal link about a vertical axis. Gravity loads the bearings, but in this idealization it contributes no torque about that axis.

Force is measured in newtons (N). Its moment about an origin is the cross product of the vector from that origin to the point of application and the force. For a planar force, the moment about the positive Z axis is `r_x F_y − r_y F_x`. A 2 N force in +Y applied 0.20 m in +X produces +0.40 N·m. A force parallel to the lever contributes zero moment. The same force at a different location can thus be easy or hard for the arm to oppose.

## Keep the wrench and its reference point together

A **wrench** packages a force and a moment about a specified origin. Suppose you know `T_A_B`, with rotation `R` and translation `t` from the A origin to the B origin in A coordinates. In 3D the same wrench expressed about the A origin is

```text
F_A = R F_B
M_A = R M_B + t × F_A
```

The force rotates, while the moment both rotates and acquires a lever-arm term. In the 2 N example, a sensor at the point of application would report zero moment for a pure force there. Shifting to the joint origin produces +0.40 N·m. A force and a velocity must use compatible frames and reference points when computing power. In particular, for a tip force and the tip's linear velocity, `F · (J q_dot) = (Jᵀ F) · q_dot`. Thus `Jᵀ F` is the vector of joint torques contributed by that force, even if the position Jacobian has no inverse. Include angular velocity and moment when working with a full wrench. [Modern Robotics on wrenches](https://modernrobotics.northwestern.edu/nu-gm-book-resource/3-4-wrenches/)

## Build a one-joint plant

The **plant** is the system you are trying to move. Its state here is joint angle `q` in radians and speed `ω` in rad/s. Let `J_eq` be the effective inertia about the joint in kg·m², `b` the viscous damping in N·m per rad/s, and `τ_load` a signed load parameter whose positive value represents a torque in the negative joint direction. The load keeps its direction if the joint reverses. Viscous damping changes sign with speed.

```text
commanded motor     clip and multiply          sum torques
torque (N·m) -----> by gear ratio G ---------> (+ applied)
                                                (- b × speed)
                                                (- load)
                                                    |
                                                    v
                                         divide by joint inertia
                                                    |
                                                    v
                                       acceleration -> speed -> angle
                                                        |          |
                                         damping uses --+          +-- log
```

The actuator adds torque. Load and damping enter the same sum. In the simulation, acceleration is the net torque divided by inertia, and integration advances speed and angle. Inverting the equation gives the applied joint torque required for a desired acceleration and speed, `J_eq × acceleration + b × ω + τ_load`. That is the difference between **forward dynamics** (input to acceleration) and **inverse dynamics** (desired acceleration to required input). With multiple joints, the mass matrix couples accelerations, and motion-dependent terms, gravity, and external contacts can matter. An isolated axis is a useful test case before introducing those couplings. [Modern Robotics on manipulator dynamics](https://modernrobotics.northwestern.edu/nu-gm-book-resource/chapter-8-1-lagrangian-formulation-of-dynamics-part-1-of-2/)

Define the ideal gear ratio as `G = ω_motor / ω_joint` with signs aligned. A 10:1 reduction multiplies the motor torque by 10 and divides its speed by 10. Power is unchanged in the ideal transmission. The rotor kinetic energy is `0.5 J_motor (G ω)²`, so the rotor contributes `G² J_motor` to effective joint inertia. With a link inertia of 0.050 and a rotor inertia of 0.00030 kg·m², the 10:1 result is 0.080 kg·m². The same gear that increases available joint torque also increases apparent inertia and reduces available joint speed for a given motor speed limit. When comparing transmissions, check both directions of this conversion and keep all loads and inertias on the same side. [Modern Robotics on gearing and friction](https://modernrobotics.northwestern.edu/nu-gm-book-resource/8-9-actuation-gearing-and-friction/)

Actual actuators can have torque limits that depend on speed, current, or temperature. Their interface might accept torque, velocity, or position, with inner loops governing the latter two. Start with the interface and the allowed operating envelope. Add friction detail if the measured residual calls for it. Viscous torque is proportional to speed. A simple Coulomb model represents sliding friction with an approximately constant opposing magnitude. Static friction can hold the mechanism still while balancing a small applied torque. A sign function with a zero value at zero speed misses that behavior and can produce numerical chatter around reversal.

Contact has a different signature. For a tabletop pusher, a normal reaction typically appears once the gap closes. A basic dry friction model bounds the tangential force by `μ N`, where `N` is the compressive normal force. A contact solver can determine the reaction consistent with constraints, or a compliant approximation can compute it from small penetration and its rate. With a stiff approximation, reduce the integration step and inspect peak force and penetration before treating a contact spike as physical. The lab below uses an imposed load, so a passing result validates the free-joint equations only. [MuJoCo computation documentation on contact and friction cones](https://mujoco.readthedocs.io/en/3.2.7/computation/index.html)

## Experiment: separate saturation from damping

Save the code as `model-joint.py` and run `python model-joint.py` with Python 3. Each trial holds a requested motor torque of 0.09 N·m from rest. The motor caps it at 0.06 N·m, so all three trials receive 0.60 N·m at the joint. Compare an unloaded joint, the same joint with an opposing torque, and the loaded joint with half the integration step. This toy axis has no position stops.

```python
from math import exp, isclose

GEAR = 10.0
INERTIA = 0.050 + GEAR**2 * 0.00030
DAMPING = 0.12
MOTOR_LIMIT = 0.06


def simulate(load, dt):
    q = speed = 0.0
    request = 0.09
    applied = GEAR * min(MOTOR_LIMIT, max(-MOTOR_LIMIT, request))
    for _ in range(round(4.0 / dt)):
        acceleration = (applied - DAMPING * speed - load) / INERTIA
        speed += dt * acceleration
        q += dt * speed
    steady_speed = (applied - load) / DAMPING
    exact = steady_speed * (1 - exp(-DAMPING * 4.0 / INERTIA))
    print(f"load={load:.2f} N m, dt={dt:.3f} s, applied={applied:.2f} N m, "
          f"angle={q:.3f} rad, speed={speed:.4f} rad/s, steady={steady_speed:.2f}")
    assert isclose(speed, exact, abs_tol=0.002, rel_tol=0)
    return abs(speed - exact)


simulate(load=0.00, dt=0.010)
coarse_error = simulate(load=0.18, dt=0.010)
fine_error = simulate(load=0.18, dt=0.005)
assert fine_error < coarse_error
```

At 4 s, speeds should be about 4.99 rad/s unloaded and 3.49 rad/s loaded. At steady speed, acceleration vanishes and damping balances the remaining torque, giving 5.00 and 3.50 rad/s respectively. The transient initially climbs more slowly in the loaded run because the net torque at zero speed is smaller. The exact speed comes from the first-order differential equation with time constant `J_eq/b`. Halving the step reduces numerical error against that reference. The requested and applied motor torques differ from the very first sample, although speed changes smoothly.

For a new model, log requested and applied torque, speed, position, and timestamps. Compare initial acceleration and the late slope separately. A wrong initial slope points to inertia, the applied torque, or an unmodeled load. An incorrect terminal speed under verified torque suggests damping or load. A discrepancy concentrated near zero speed suggests stiction, backlash, or measurement quantization. Fit parameters on one simulated or recorded trace and check a different load or reversal before treating the fit as general. Commission a physical axis only under supervision with its approved motion, torque, and travel limits.

## Exercises

1. The simulated joint must sustain 4 rad/s against a 0.18 N·m load. Does changing the controller gain make this feasible with the given cap?

<details>
<summary>Solution</summary>
<p>At steady speed the required torque is 0.12 × 4 + 0.18 = 0.66 N·m. The available torque is 0.60 N·m. A gain change cannot provide missing steady torque. The model predicts a ceiling of 3.50 rad/s for this load.</p>
</details>

2. A simulated force sensor is 0.20 m along base +X, with its +X pointing along base +Y and its +Z along base +Z. It reports a 2 N force along sensor +X with zero moment. What base-frame wrench components act at the joint origin?

<details>
<summary>Solution</summary>
<p>Rotate the force into base coordinates to get (0, 2, 0) N. Shift the moment to the base origin with t × F, which gives (0, 0, 0.40) N·m. Rotating the reported zero moment alone would miss the load on the joint.</p>
</details>

## Summary

- Add torques about a common axis and reference point to predict acceleration. Model the rotation and reference point of an external wrench.
- Gearing trades speed for torque and reflects rotor inertia by the square of the ratio. Damping, static friction, and contacts produce different motion signatures.
- Compare simulated traces against analytical cases and inspect applied limits before tuning. A model of required torque also supplies feedforward for [trajectory tracking](/notes/trajectory-and-control/).
