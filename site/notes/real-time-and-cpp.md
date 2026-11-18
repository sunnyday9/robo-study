---
title: Real-time budgets and C++ in ROS 2
topic: Field engineering
order: "121"
description: Turn a control rate into deadlines, measure release and execution delays, and decide where C++ and a watchdog belong.
prerequisites: Robot systems and embedded control, plus basic familiarity with ROS 2 topics. The lab requires Python 3.
minutes: 50
---

## A rate tells you when to start planning the budget

A rover speed controller running at 200 Hz has a 5 ms period. If a sensor read starts late, an update may finish at 6 ms even when the controller itself takes only 1 ms. During those extra milliseconds, the drive holds the previous output and the next calculation may begin with a different sample interval. A good average rate can hide those events. Give the loop a deadline with a specified response when it misses. A soft deadline miss can degrade quality. For a hard deadline, any miss violates the requirement and the timing argument needs more than a benchmark.

For cycle `k`, let `rₖ = r₀ + kT` be its intended release on a monotonic clock, `sₖ` its actual start, `fₖ` its completion, and `D` its relative deadline. Release lateness is `sₖ − rₖ`, elapsed execution is `fₖ − sₖ`, and response time is their sum `fₖ − rₖ`. Compare the last quantity with `D`. Actual start spacing `sₖ − sₖ₋₁` measures cycle-to-cycle jitter against `T`. Label which metric you mean by jitter. Sensor age at application is yet another quantity. It includes time before the cycle starts and can exceed the budget even when the computation meets its own deadline.

```text
 One illustrative cycle, elapsed from intended release

 planned        actual       read        control        output     deadline
 release        start        done        done           applied    for cycle
 0 ms --------- 0.7 -------- 1.5 ------- 2.5 ---------- 3.7 ------ 5.0 ms
       0.7 wait      0.8 I/O      1.0 math      1.2 commit    1.3 slack
```

The timeline spends 3.7 ms of 5 ms, including scheduler wait. A budget review could allocate exactly those amounts to wakeup, input, calculation, and output, and keep the 1.3 ms as margin. The numbers are illustrative. In a design review, bound each stage under the intended load and check how the bounds were obtained. A software write completing at 3.7 ms is evidence of physical application only if the measurement boundary includes the device. For the teaching rover, keep the 5 ms wheel loop and 50 ms command lease on the MCU. A host-side measurement then supports the host portion of the argument.

## Place the critical path before choosing a language

Use Python to explore controller math, drive simulations, inspect traces, and prototype a ROS graph with `rclpy`. Keep it for components whose measured timing and runtime assumptions satisfy their requirements. For CPU work where you need tighter control over data representation, allocations, and thread behavior, put the hot path in C++ and use `rclcpp` at the host boundary. Keep the control update as a small function with explicit input, output, state, and elapsed time. Feed it the same fixtures used for the Python reference. Check signs, units, saturation, reset behavior, and tolerance before comparing performance.

A `rclcpp` subscription takes in data via an executor, which schedules callbacks for subscriptions, timers, and other entities. On a single executor thread, a long callback can delay a ready timer. In a multithreaded executor, callbacks in a mutually exclusive group still exclude each other. Lay out the groups and threads, and write down which state they share. One layout gives the time-sensitive loop a bounded latest-sample handoff and moves reporting and service calls to another context. A bounded handoff needs an explicit rule when full and the controller still checks sample age when it reads. Measure the costs of middleware delivery, callback dispatch, and handoff separately if the delays overlap in your end-to-end record. [ROS 2 Jazzy executor documentation source](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/Concepts/Intermediate/About-Executors.rst) · [ROS 2 communication](/notes/ros2-communication/)

Initialize and preallocate before the timed path. Audit resize operations, message construction and publication, formatted logging, file I/O, and locks. A high-priority thread waiting on a lock held by lower-priority work can miss a deadline even when CPU usage is low. The ROS 2 real-time tutorial calls out page faults, dynamic allocation and deallocation, and indefinitely blocking synchronization as sources of nondeterminism. On supported Linux systems, PREEMPT_RT makes more kernel work preemptible, including much interrupt work. Review priorities and competing workloads with the platform owner before testing scheduling changes on a dedicated system. C++ and PREEMPT_RT each leave the application responsible for bounded work and for evidence on the target configuration. [ROS 2 Jazzy real-time tutorial source](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/Tutorials/Demos/Real-Time-Programming.rst) · [Linux PREEMPT_RT theory](https://docs.kernel.org/core-api/real-time/theory.html)

## Lab — measure the start and finish of a periodic loop

Save as `timing.py`. Run `python timing.py`, then `python timing.py --delay`, on a normal laptop with Python 3.7 or later. The second run explicitly stalls several cycles to model waits for an external dependency. Both runs use `monotonic_ns()` for elapsed time and sleep toward absolute intended release times, so a late cycle does not shift the rest of the schedule. `sleep` can return late because of scheduling. The script drops releases crossed by previous work and counts them separately. These calls run on the ordinary host scheduler. [Python clock and sleep documentation](https://docs.python.org/3/library/time.html)

```python
import math
import sys
import time

PERIOD_NS, SLOTS = 5_000_000, 200
inject_delay = "--delay" in sys.argv
release_zero = time.monotonic_ns() + PERIOD_NS
records = []
slot = skipped = 0

while slot < SLOTS:
    release = release_zero + slot * PERIOD_NS
    remaining = release - time.monotonic_ns()
    if remaining > 0:
        time.sleep(remaining / 1_000_000_000)
    start = time.monotonic_ns()
    sum(i * i for i in range(200))
    if inject_delay and slot % 40 == 10:
        time.sleep(0.013)
    finish = time.monotonic_ns()
    records.append((slot, start - release, finish - start, finish - release))
    next_release = (finish - release_zero + PERIOD_NS - 1) // PERIOD_NS
    next_slot = min(SLOTS, max(slot + 1, next_release))
    skipped += next_slot - slot - 1
    slot = next_slot

late_slots = [row[0] for row in records if row[3] > PERIOD_NS]
for name, column in (("start lateness", 1), ("work elapsed", 2), ("response", 3)):
    values = sorted(row[column] for row in records)
    p99 = values[math.ceil(0.99 * len(values)) - 1]
    print(f"{name}: p99 {p99 / 1e6:.3f} ms, max {values[-1] / 1e6:.3f} ms")
print(f"late completed slots: {late_slots}")
print(f"{len(late_slots)} late completions + {skipped} skips / {SLOTS} releases")
```

On a quiet machine with sufficiently precise sleeps, expect few misses in the baseline. If all five injected stalls run, each takes longer than its 5 ms deadline and skips at least two releases. Expect slot numbers near 10, 50, 90, 130, and 170 in the late list, with at least ten skips when all injections run. Scheduler spikes can add misses or skip an injection slot. Repeat under a representative load and keep each run's results. If start lateness grows while elapsed work stays flat, investigate dispatch delay. If only elapsed work grows, split it into compute, waits, and commit time. Work elapsed includes any time the thread was preempted during work, so a long sample alone cannot identify the cause. This script deliberately allocates test records, has no ROS runtime, and executes no motor commands.

## Decide how a late update fails

Executing a backlog of old updates can magnify a fault. For a latest-value controller, skip obsolete releases and check fresh input before the next calculation. Record skipped releases and consecutive misses. Have the receiving MCU enforce command freshness on its own clock. Separately consider a hardware watchdog for loss of MCU progress. Feed it after the required work proves progress, rather than from a timer interrupt that can keep running through a deadlocked controller. A watchdog reset changes system state. Review the default outputs, initialization, fault reporting, and supervised restart sequence. The protective path still needs a machine-specific review.

## Exercises

**1. Investigate a regression.** The baseline reaches 0.8 ms start lateness and 0.4 ms work at p99. A loaded run reaches 3.4 ms and 0.5 ms respectively. Which measurement should guide your first change?

<details>
<summary>Solution</summary>

Start by measuring wait before callback entry, where the larger change appears. Compare callback ready time, dispatch time, and overlap with other work under the same replay. Analyze each sample's response directly. The p99 of the sum need not equal the sum of the two p99 values.

</details>

**2. Test watchdog independence.** A host heartbeat stays green after the planner deadlocks while a send thread keeps emitting its last target. What failure should a dry run expose?

<details>
<summary>Solution</summary>

Freeze planner progress in the simulated trace while the sender continues. Check whether old target data still renews the receiver's lease. Bind freshness to valid control progress and define when a repeated value carries a new valid observation. Assert the stale-output transition by a specified deadline and require a fresh session for recovery.

</details>

## Summary

Budget each stage against an intended release and report both late completions and skipped releases. Use Python for a reference and instrumented experiments, and use C++ where the measured critical path requires control over allocation and execution. Design freshness checks and watchdog behavior to survive the failures they are supposed to detect.
