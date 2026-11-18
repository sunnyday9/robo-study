---
title: Commissioning and diagnostics
topic: Field engineering
order: "122"
description: Use a staged acceptance plan and trace the first broken boundary before changing a rover controller.
prerequisites: Robot systems and embedded control, plus the distinction between ROS time and elapsed time. The lab is a Python-only dry run.
minutes: 50
---

## Commission one claim at a time

A rover turns in the wrong direction in its first integration test. An engineer might reverse a motor in configuration, change a TF frame, or add a minus sign to the yaw controller. Each change could hide an error at another boundary. Commissioning starts with the installed machine and its intended use, then checks progressively larger claims against a known configuration. Start from one command with a known expected response. Trace the command through conversion to wheel targets, receiver acceptance, and measured response. Fix the first boundary that violates its contract.

Write the acceptance plan while you can still change the design. Identify the responsible supervisor, permitted area and machine state, protective functions, abort conditions, and evidence needed to advance. An emergency stop, drive inhibit, normal controlled stop, and isolation procedure are distinct mechanisms with different effects. Physical checks and recovery follow the approved procedure for the specific machine. The work below runs offline. [NASA verification and acceptance planning](https://www.nasa.gov/reference/system-engineering-handbook-appendix/)

| Stage | Claim and evidence to take forward |
| --- | --- |
| Bench review with actuation isolated under the site procedure | Record the as-built component IDs, approved firmware and configuration, mechanical dimensions, signs, and sensor/drive limits. Compare part and calibration versions to the plan. Use synthetic inputs and an inert output sink for software checks. |
| Closed-loop simulation | Check forward travel, a left turn, and input loss against explicitly named units, reset conditions, and time limits. Collect a commanded-versus-applied target trace and compare simulated pose against the expected direction. |
| Integrated dry run | Compare the versioned launch configuration, command routing, and acceptance logs to the plan while actuation stays isolated. Check that startup and missing data produce the expected inhibited state. HIL can exercise real controller I/O against a simulated plant in a qualified setup. |
| Supervised physical acceptance | The responsible team authorizes a machine-specific test in a controlled space after reviewing the preceding evidence. They verify safeguards, define movement limits, and measure actual response and stopping clearance under the approved plan. Any failed prerequisite holds the stage. |

Before a dry run, record which configuration guarantees an inert sink. A dashboard displaying zero speed cannot establish that an actuator is isolated. Define aborts that include lost observation, uncertain isolation, changed configuration, and loss of supervisor control. Preserve the failing trace and return to the previous demonstrated stage after resolving the cause. An illustrative gate such as “modeled target zero within 55 ms of the last accepted command” needs its own evidence. A physical stop gate separately specifies what counts as stopped, measurement uncertainty, the starting conditions, and the space the machine is allowed to traverse.

## Follow the first missing or inconsistent observation

For the teaching rover, positive yaw commands ask the right wheel to turn faster than the left. A `0.20 m/s`, `+0.40 rad/s` command gives `2.8` and `5.2 rad/s` with the geometry defined in [Robot systems and embedded control](/notes/robot-systems-and-embedded/). If both measured wheel signs and magnitudes agree but the simulated pose turns right, check the pose axes and integration geometry. If the target values are already swapped at the adapter, investigate wheel indexing before the pose calculation. For a tabletop arm, apply the same reasoning to named joint targets, signs, and frames.

```text
 Symptom: the applied wheel target unexpectedly goes to zero
 |
 +-- Producer emits no new sequence ---> check planner progress and input age
 +-- Sends continue, ingress is quiet --> check link, queues, and ingress logging
 +-- Ingress continues, rejects rise ---> read session, sequence, or range reason
 +-- Valid receives continue -----------> inspect local inhibit and commit state
     |
     +-- Applied target valid, motion differs -> examine feedback or plant evidence
```

This tree orders observations by boundary. It narrows a search without proving a cause. For example, no ingress record can mean loss, a receiver reset, or a dropped log entry. Record input age, boot identity, uptime, monotonic timestamp and clock ID, command session and sequence, accept or reject reason, inhibit state, output target, and wheel feedback with units. Include dropped-log or overwritten-buffer counts. Preserve the pre-fault window with a bounded recorder and write it out away from time-sensitive work. ROS `DiagnosticStatus` supplies a component name, hardware ID, levels including `STALE`, and key-value fields. Use diagnostics for visibility and keep the time-critical interlock path independent. [Jazzy DiagnosticStatus definition](https://raw.githubusercontent.com/ros2/common_interfaces/jazzy/diagnostic_msgs/msg/DiagnosticStatus.msg)

Join host and MCU records by session and sequence. Calculate the lease on the receiver's steady clock. To estimate one-way delay across machines, you need a defensible clock mapping with uncertainty. Otherwise report sender intervals and receiver intervals separately. Keep simulation stamps for replay and record real elapsed time as a separate measurement. A simulated clock can pause, jump, or run faster than wall time. [ROS 2 clock and time design](https://design.ros2.org/articles/clock_and_time.html) · [Frames and time](/notes/ros2-frames-and-time/)

## Lab — separate a missing receive from a rejected command

Save as `dry_run.py` and run `python dry_run.py healthy`, `python dry_run.py gap`, and `python dry_run.py reject`. Each run generates complete in-memory telemetry on one simulated clock. The host sends every 20 ms and the receiver evaluates its lease every 5 ms. The session starts with the first valid command at time zero. The `gap` case suppresses ingress after 40 ms while the host continues to create commands. The `reject` case delivers those commands with a bad session. Output is a pair of numbers representing modeled left and right targets in rad/s.

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("case", choices=("healthy", "gap", "reject"))
case = parser.parse_args().case
trace = []
last_valid = expired_at = None
target = (0.0, 0.0)

for t in range(0, 111, 5):
    if last_valid is not None and expired_at is None and t - last_valid >= 50:
        expired_at, target = t, (0.0, 0.0)
        trace.append((t, "output", f"expired, L/R={target} rad/s"))
    if t % 20:
        continue
    seq = t // 20 + 1
    trace.append((t, "send", seq))
    if t > 40 and case == "gap":
        continue
    trace.append((t, "ingress", seq))
    if t > 40 and case == "reject":
        trace.append((t, "reject", "wrong session"))
    elif expired_at is None:
        last_valid, target = t, (2.8, 5.2)
        trace.append((t, "accept", seq))
        trace.append((t, "output", f"L/R={target} rad/s"))

for t, stage, value in trace:
    print(f"{t:3} ms  {stage:7}  {value}")
if expired_at is None:
    print(f"last accepted {last_valid} ms, no expiry")
else:
    elapsed = expired_at - last_valid
    print(f"last accepted {last_valid} ms, elapsed to zero {elapsed} ms")
```

In the healthy trace, sequence 6 is accepted at 100 ms with targets `(2.8, 5.2)`. Both fault cases last accept sequence 3 at 40 ms and produce zero at 90 ms, which meets the illustrative 55 ms gate with 5 ms of margin. In `gap`, the first missing boundary is ingress for sequence 4 at 60 ms. In `reject`, sequence 4 reaches ingress at 60 ms and immediately records `wrong session`. Keep those fingerprints in your acceptance record alongside the output latency. Add checks for the last accepted sequence, first affected sequence, cause reported at the rejecting boundary, and final state. The lab exercises trace interpretation on synthetic data. It has no robot driver or timing model for actual braking.

## Exercises

**1. Repair the measurement plan.** Field records show sequence 4 sent and output going to zero. The ingress log has a gap, but its overwritten-record counter increased. What can you conclude, and what do you collect next in a dry run?

<details>
<summary>Solution</summary>

The send and output transitions are observed. The sequence 4 ingress outcome is unknown. Record device boot ID, per-stage counts and last sequence, and the reject reason. Repeat the same input with a bounded pre-fault record and confirm buffer coverage over the event. Distinguish a communication gap from a logging gap before assigning the cause.

</details>

**2. Review the acceptance record.** A fixture shows zero target at 90 ms with last acceptance at 40 ms. Someone claims the machine stops within 55 ms of link loss. Rewrite the claim and name the missing evidence.

<details>
<summary>Solution</summary>

In this fixture the model changed its target to zero 50 ms after the last accepted command. To measure a physical stop, the acceptance plan must define and observe the start event independently, record calibrated speed or position, define a stop threshold and uncertainty, and cover approved cases such as differing initial speeds and surfaces. The responsible team owns that supervised test.

</details>

## Summary

Commission in stages with a narrowly scoped acceptance record at each boundary. Correlate send, ingress, acceptance, and output by sequence. Diagnose from the first missing or inconsistent observation, and qualify your conclusion by the completeness and timing of the evidence.
