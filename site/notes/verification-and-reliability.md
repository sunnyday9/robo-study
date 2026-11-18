---
title: Verification and reliability for robots
topic: Field engineering
order: "123"
description: Turn a command-loss requirement into a testable invariant, exercise faults, and preserve evidence another engineer can audit.
prerequisites: Commissioning and diagnostics, basic Python unit tests, and the rover command-lease example.
minutes: 55
---

## Write the requirement before the test

When a robot passes one simulation, ask what was exercised and what could still fail. Verification checks a specified requirement. Validation asks whether the resulting product meets the intended need in its environment. For the rover, “zero modeled target within 55 ms of the last accepted command” is a verification claim. Whether the rover can work around people within a safe operating envelope needs evidence about the actual machine, the environment, and its intended use. A good evidence record lets the next engineer tell these claims apart. [NASA Systems Engineering Handbook, product realization](https://www.nasa.gov/reference/5-0-product-realization/)

Write an ID, initial state, stimulus, measurement point, tolerance, and failure response. For example, requirement `CMD-01` starts from an active session with a valid nonzero target. If no valid command arrives before the 50 ms lease expires, with 5 ms periodic checks, the modeled output must be zero within 55 ms of the last acceptance and stay zero until an explicit rearm and a valid command from the new session. Duplicates, invalid values, and earlier sessions cannot extend a lease. Use receiver-local monotonic milliseconds for this test. A firmware requirement would also specify scheduling assumptions and the output observation point. The 5 ms allowance is for check phase and leaves no implicit allowance for lateness beyond the stated deadline.

```text
 CMD-01       input fixture + independent expected outcomes
                          |
                          v
           [controller under test] ---> observed state and timestamp
                          |                       |
                          +---------> compare <---+
                                         |
                            gate result + retained trace
```

Here the comparison uses the fixture's expected outcomes and the observed data. Keep the assertions independent of the controller implementation. A test that computes the expected timeout by calling the same timeout function will reproduce mistakes in both places. Also check that output was nonzero before the fault. An implementation stuck permanently at zero can appear to handle command loss if you only inspect the final sample.

## Put each gate where the relevant failure can happen

| Gate | What to run and what it can establish |
| --- | --- |
| Pure functions and protocol state | Check clamping, sign, range, sequence handling, expiry boundaries, and reboot behavior with fixed fixtures. Run on every change. |
| Software-in-the-loop (SIL) | Run the controller software against a simulated plant and virtual I/O. Test closed-loop behavior under changes in delay, friction, and sensor noise. Record what artifact ran, how time advanced, and what the plant omitted. The Python lab below only models protocol state. |
| Hardware-in-the-loop (HIL) | Use the intended controller hardware with a real-time simulated plant and representative interfaces in an approved setup. This can reveal target CPU, peripheral, and protocol timing defects. Check simulator overruns so its own missed steps do not masquerade as controller faults. |
| Supervised physical acceptance | Use the approved machine procedure and the installed configuration to evaluate effects that depend on the real mechanism and workspace, such as traction, brake response, and operator recovery. |

Match fault injection to the claim. Dropping messages before the parser tests stale-input handling. Corrupting a field at the parser tests rejection and resynchronization. A simulation that directly zeros the output bypasses both. Include expected negative tests, such as rejection of an old command after rearming, alongside positive controls. Keep injected stimuli confined to offline test harnesses or separately approved test equipment. [MathWorks SIL and HIL comparison](https://www.mathworks.com/discovery/hardware-in-the-loop-hil.html)

## Lab — check phase, replay, and recovery on CPU

Save as `reliability.py` and run `python reliability.py -v`. The fixture evaluates arrivals at their stated millisecond and checks expiry at arrivals and at each 5 ms tick. Output is an in-memory scalar wheel target in rad/s. Session 1 is initially authorized with zero output. A reset clears permission. An `arm` event represents an authorization already granted by the test harness. The model includes no physical device and the expected windows below are written independently of the code that generates output.

```python
import unittest


def simulated_targets(events):
    session, seq, last, target = 1, 0, None, 0.0
    outputs = []
    for now in range(111):
        event = events.get(now)
        if (now % 5 == 0 or event is not None) and last is not None and now - last >= 50:
            session, last, target = None, None, 0.0
        if event is not None:
            kind, epoch, number, value = event
            if kind == "reset":
                session, last, target = None, None, 0.0
            elif kind == "arm" and session is None:
                session, seq, last = epoch, 0, now
            elif kind == "frame" and session == epoch and number > seq and abs(value) <= 8.0:
                seq, last, target = number, now, value
        outputs.append(target)
    return outputs


class LeaseTests(unittest.TestCase):
    def test_valid_update(self):
        out = simulated_targets({21: ("frame", 1, 1, 2.8), 61: ("frame", 1, 2, 3.0)})
        self.assertEqual(out[20:22], [0.0, 2.8])
        self.assertEqual(out[61:], [3.0] * 50)

    def test_silence_after_off_tick_arrival(self):
        out = simulated_targets({21: ("frame", 1, 1, 2.8)})
        self.assertEqual(out[21:75], [2.8] * 54)
        self.assertEqual(out[75:], [0.0] * 36)

    def test_bad_frames_do_not_renew(self):
        out = simulated_targets({
            21: ("frame", 1, 1, 2.8),
            60: ("frame", 1, 1, 7.0),  # Duplicate.
            70: ("frame", 1, 2, 8.1),  # Out of range.
        })
        self.assertEqual(out[60:76], [2.8] * 15 + [0.0])

    def test_arrival_on_expiry_cannot_renew(self):
        out = simulated_targets({20: ("frame", 1, 1, 2.8), 70: ("frame", 1, 2, 3.0)})
        self.assertEqual(out[69:71], [2.8, 0.0])

    def test_reset_and_rearm(self):
        out = simulated_targets({
            21: ("frame", 1, 1, 2.8),
            40: ("reset", 0, 0, 0.0),
            50: ("frame", 1, 2, 2.8),
            60: ("arm", 2, 0, 0.0),
            65: ("frame", 1, 3, 2.8),
            75: ("frame", 2, 1, 2.8),
        })
        self.assertEqual(out[39:76], [2.8] + [0.0] * 35 + [2.8])


if __name__ == "__main__":
    unittest.main()
```

Expect five passing tests. In the off-tick case, the last command arrives at 21 ms, the deadline for renewing the lease is 71 ms, and the next tick is 75 ms. The zero transition is 54 ms after acceptance. The arrival-on-expiry case tests a different failure. If processing accepts the arrival at 70 ms before checking age, it extends an already expired lease. Temporarily change `>= 50` to `> 50` in a scratch copy and rerun. Expect the arrival-on-expiry test to fail even though the off-tick case can still pass. Revert the edit before testing other changes. The suite exercises outputs of this Python model. A production gate should run the real software or hardware artifact by the method named in its verification plan.

## Turn test evidence into operational reliability

Keep evidence per requirement and configuration. Include the controller build or firmware hash, parameters, element IDs, test harness version, seed or fixture, timing origin, pass criteria, raw result, and observed failure reason. Save a passing trace and a failing trace that demonstrates a test catches the intended condition. Record skipped checks and their reasons. A change to command handling warrants rechecking lease semantics. A change to tires or payload warrants reviewing the earlier evidence for traction and stopping. Track availability using an exposure denominator, such as faults per hour of operation in a declared configuration, and also track recovery time and repeat failures.

Zero failures in 100 independent trials from the same intended population gives an exact one-sided 95% upper failure-probability bound of about 2.95%. Solve `(1 − p)^100 = 0.05` for `p`. This estimate depends on independent trials at a common probability. Running a deterministic fixture 100 times exercises repeatability within that fixture. It supplies no population-level failure rate. For broader reliability work, predefine the workload mix and include restarts, repeated operating cycles, and recorded configuration changes. [NIST exact binomial confidence limits](https://itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbici.htm)

Give the on-call engineer a runbook for command expiry. Name the alert and expected stopped or inhibited state, identify who takes control under the approved procedure, and preserve the trace before a restart can overwrite it. Have them confirm the boot ID, command sequence progression, reject counters, and last authorized configuration. Reproduce offline, record one controlled change, and repeat the affected gates. Assign a maintenance owner to monitor connector faults, encoder calibration drift, battery condition, and repeated resets across operating hours. After replacement or firmware changes, tie the checks you repeat to the dependencies that changed.

## Exercises

**1. Add a timing fault.** The local task skips the check at 75 ms after a command accepted at 21 ms, and resumes at 80 ms. How should a test expose it?

<details>
<summary>Solution</summary>

Allow the harness to suppress the 75 ms tick for this fixture. With no further arrivals, record the output each millisecond until 80 ms. The first zero is 59 ms after acceptance. An independent oracle should fail `CMD-01` because output was still nonzero at 76 ms. Investigate scheduling bounds or an independently timed protective mechanism before claiming the same limit for a target system.

</details>

**2. Decide what evidence to repeat.** A replacement MCU passes the pure protocol gate, but the integrated dry run shows intermittent resets. The last physical acceptance used the original board. What status do you record and what do you investigate first?

<details>
<summary>Solution</summary>

Record protocol pass, integrated dry-run failure, and physical acceptance pending for the replacement configuration. Save board and firmware IDs, uptime, reset reason, supply telemetry if available, and traffic before the reset. Compare the last passing configuration with the current one and reproduce under the isolated test setup. After resolving the cause, repeat affected integration gates and bring the evidence to the supervisor before advancing.

</details>

## Summary

Define pass criteria before running the test. Use protocol checks, SIL, HIL, and supervised acceptance for failures each can observe. Preserve versioned evidence, inject faults with an independent oracle, and keep runbooks and maintenance checks tied to the configurations that earned acceptance.
