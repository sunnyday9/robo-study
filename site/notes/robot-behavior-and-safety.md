---
title: "Robot behavior and safety"
topic: "Planning and autonomy"
order: "053"
description: "Build a small task executive that handles stale sensing, missed deadlines, and loss of commands, then test its invariants."
prerequisites: "Navigation systems and Python functions and classes."
minutes: 55
---

## Decide what the robot may do next

A rover accepts a request to reach a charging bay. While it is driving, localization may become invalid, the request may be cancelled, or the task process may stop running. A **task executive** owns the goal lifecycle and decides whether to plan, start motion, wait, recover, or report failure. It coordinates planners and controllers by asking them to do work, observing results, and revoking authorization when an assumption changes.

A **finite-state machine** (FSM) stores a named state and moves between states using events and guards. List the transitions for an approach task. From `IDLE`, start only with an accepted goal and valid inputs. In `DRIVING`, loss of a precondition has priority over nominal completion. Reaching the goal region requests a stop and transitions to `STOPPING`. A fresh standstill observation permits `DONE`. Recovery from a latched fault requires an explicit reset after the cause is understood. This makes the decision about simultaneous events visible in one place.

```text
 IDLE -- accepted goal --> DRIVING -- in goal region --> STOPPING
                              |                            |
                              |                     standstill seen
                              |                            v
                   invalid input or deadline             DONE
                              v
                         FAULT (latched)
                              ^
                              +--- STOPPING can fault too

 DRIVING renews a command lease. Without renewal, the receiver requests zero.
```

The first row traces normal progress. Both active states can fault. The receiver's expiration rule also applies when the executive stops ticking and cannot transition at all.

## Choose a representation for failure and interruption

A **behavior tree** (BT) evaluates nodes by ticking the root. A leaf can report success, failure, or running. A sequence composes successive steps and a fallback tries alternative branches after failure. This fits a task with reusable subtrees such as “reach the bay” and “wait for a clear path.” Check the semantics of the exact control node. In BehaviorTree.CPP, a reactive sequence can recheck a condition while a later asynchronous action is still running, whereas a standard sequence can resume at that running child. Make the action cancellable. A node stopping its own computation must be connected to cancellation, acknowledgement, and command ownership outside the tree. [BehaviorTree.CPP reactive and asynchronous behavior](https://behaviortree.dev/docs/tutorial-basics/tutorial_04_sequence/)

An FSM makes transition ordering and terminal states straightforward to audit. A BT helps when behaviors share substeps and recovery options. Either design can accidentally issue two motion commands if an old action outlives a transition. Use a stable goal identifier, a single motion owner, and a way to reject late results and commands after cancellation or supersession. Put time and retry budgets around each asynchronous operation. An operation that has been requested, one that has been accepted, and one that has completed are separate states of knowledge. [ROS 2 actions](/notes/ros2-communication/)

## State invariants before writing transitions

An **invariant** is a property that should hold throughout execution. For this rover, require that the executive only emit a nonzero motion request if the task is driving, inputs are fresh, and the task deadline has yet to expire. The receiver accepts a nonzero request only while its lease is live. Fault stays latched across later good observations. Finish a successful approach only with a fresh standstill observation. Specify the clock domain and boundary rule for each inequality. A deadline bounds task completion. A watchdog detects absence of expected activity. A heartbeat derived from a timer alone can keep arriving even when useful work is wedged, so define what a renewal certifies.

Fail-safe design requires deciding the system's response to specific failures and moving to a state that reduces risk. A requested zero velocity and observed standstill are distinct. Some hazards require a verified controlled stop or holding a load. A stop function implemented as a Python condition depends on the executing process, input validity, communications, and the downstream controller. A safety-rated architecture requires assessment and validation of the full safety function, from the sensing and logic to the actuator response, against the machine hazards and applicable requirements. It may need an independent safety-related channel with its own diagnostics and validated timing. The exercise below is an application-level simulation. Commission any physical system under qualified supervision with appropriate protective measures and a validated stop function. [ISO 13849-1:2023 scope](https://www.iso.org/standard/73481.html)

## Lab: remove the task process from a deterministic schedule

Save as `executive.py` and run `python executive.py`. All time values are integer milliseconds on one synthetic monotonic clock. One invocation of `tick` processes the current sample. A Boolean `stopped` stands for measured standstill from the same sample as the scan in this lab. The receiver is modeled as a separate function of time and the last command. Calling it while withholding executive ticks injects a process stall. In a deployed system that timing function needs a real independent scheduling boundary and verified clock and transport behavior.

```python
from dataclasses import dataclass

MAX_AGE, LEASE, DEADLINE = 80, 100, 500


@dataclass(frozen=True)
class Command:
    speed: float             # m/s
    expires_ms: int


def receiver_speed(command, now):
    return command.speed if now < command.expires_ms else 0.0


class Executive:
    def __init__(self, start_ms):
        self.state = "DRIVING"  # one goal accepted by the simulated caller
        self.deadline = start_ms + DEADLINE
        self.reason = ""

    def tick(self, now, sample_ms, goal=False, stopped=False):
        if self.state in {"DRIVING", "STOPPING"}:
            if not 0 <= now - sample_ms <= MAX_AGE:
                self.state, self.reason = "FAULT", "stale input"
            elif now >= self.deadline:
                self.state, self.reason = "FAULT", "deadline"
            else:
                if self.state == "DRIVING" and goal:
                    self.state = "STOPPING"
                if self.state == "STOPPING" and stopped:
                    self.state = "DONE"
        speed = 0.20 if self.state == "DRIVING" else 0.0
        expires = min(now + LEASE, sample_ms + MAX_AGE + 1, self.deadline)
        return Command(speed, expires)


executive = Executive(0)
last = executive.tick(20, 10)
assert receiver_speed(last, 90) == 0.20
assert receiver_speed(last, 91) == 0.0  # no executive tick
assert executive.state == "DRIVING"
print("stall: receiver requests zero at 91 ms")

assert executive.tick(120, 10).speed == 0.0
assert executive.tick(140, 140).speed == 0.0
assert (executive.state, executive.reason) == ("FAULT", "stale input")
print("resumed tick:", executive.state, executive.reason)

executive = Executive(0)
assert executive.tick(100, 99, goal=True).speed == 0.0
assert executive.state == "STOPPING"
assert executive.tick(130, 130, stopped=True).speed == 0.0
assert executive.state == "DONE"
print("goal with standstill:", executive.state)

executive = Executive(0)
last = executive.tick(499, 499)
assert receiver_speed(last, 499) == 0.20
assert receiver_speed(last, 500) == 0.0
assert executive.tick(500, 500, goal=True, stopped=True).speed == 0.0
assert (executive.state, executive.reason) == ("FAULT", "deadline")
print("goal at deadline:", executive.state, executive.reason)
```

The receiver drops the request at 91 ms because the observation was taken at 10 ms and remains valid through age 80 ms inclusive. The command also expires by the task deadline and, independently, by its maximum lease. Test one tick on either side of each boundary. In simulation, record goal ID, transition reason, first bad input age, command expiry, time to zero request, and time to actual standstill. Inject old messages, task cancellation during recovery, and loss of control feedback. If the executive's log says stopped but simulated wheels still turn, trace from command acceptance to measured response.

## Exercises

1. A delayed packet for an earlier goal arrives after that goal has been cancelled and a new goal accepted. Extend the receiver contract so the earlier nonzero command cannot take effect even if its lease is still live.

<details>
<summary>Solution</summary>

Give each motion authorization an epoch and each command a sequence number for that epoch. The receiver accepts only its current authorized epoch and a sequence greater than the last one accepted. Revocation retires the epoch and discards the stored command. Test by delivering a live command from the old epoch after revocation, then delivering a reordered command within the new epoch. The original expiry check still applies.

</details>

2. Demonstrate a case in which the lease, rather than observation age or task deadline, is the first timeout. Then compare expiry when the receiver incorrectly starts the lease on arrival.

<details>
<summary>Solution</summary>

For this experiment, change `MAX_AGE` to 200. At `now = sample_ms = 20`, the three expiry candidates are 120, 221, and 500 ms. Assert that the receiver requests motion at 119 ms and zero at 120 ms. Deliver the command at 90 ms. Starting a fresh lease on arrival would extend it to 190 ms, hiding 70 ms of transport delay. Retain the original expiry under the shared clock assumption.

</details>

## Summary

An executive should make guard priority, cancellation, and completion observable. An independently enforced deadline or lease can withdraw commands when the executive goes silent. Test fault traces and physical stop behavior separately from nominal task success, and treat safety-rated protection as a system engineering responsibility.
