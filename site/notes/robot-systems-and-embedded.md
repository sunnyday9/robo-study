---
title: Robot systems and embedded control
topic: Field engineering
order: "120"
description: Divide a rover between a host, a microcontroller, and motor drives, then test what happens when a command stream goes silent.
prerequisites: Python functions and basic feedback loops. The lab requires Python 3 and a terminal.
minutes: 50
---

## Decide what must keep working when the host stalls

An indoor rover has two driven wheels. Its host computer estimates pose, plans a route, and sends desired forward speed and yaw rate. With wheel radius `r` and contact-track width `b` in meters, the ideal no-slip wheel targets are `left = (v − bω/2) / r` and `right = (v + bω/2) / r`, both in radians per second. Positive wheel rates propel the rover forward. With `v = 0.20 m/s`, `ω = +0.40 rad/s`, `r = 0.05 m`, and `b = 0.30 m`, the targets are `2.8` and `5.2 rad/s`. The right wheel travels faster for a left turn in the `base_link` convention of forward X, left Y, and up Z. Slip and effective radius change the motion that actually results. [ROS REP 103](https://raw.githubusercontent.com/ros-infrastructure/rep/master/rep-0103.rst) · [Coordinate frames](/notes/coordinate-frames/)

The process that computes those targets can stall while a camera allocates a frame or a planner searches a crowded map. A microcontroller (MCU) can sample encoders, regulate wheel speed, and expire host commands on a local clock even during that stall. The drive supplies and regulates motor power. Some drives already close current and velocity loops, in which case the MCU can supervise targets and feedback instead of duplicating those loops. Give each loop one owner. For the teaching rover, the host sends wheel targets every 20 ms, the MCU checks them every 5 ms, and the modeled command lease expires 50 ms after the last accepted receive event. Choose those rates by analyzing dynamics and failure paths for an actual design.

```text
 Host: planner -> wheel targets -- commands --> MCU: validate -> speed control
                  diagnostics <-- telemetry --      ^                 |
                                                     |                 v
                                wheel encoder counts +-- wheels <-- motor drive

 Independent protective path --------------------------> drive inhibit, if designed for it
 MCU local clock ----------------> expire stale commands even if host is silent
```

The arrows show two feedback paths. Encoder feedback is local to the speed loop, while telemetry informs the host. A separately engineered protective path addresses hazards even when the host or MCU stops executing. Deciding what the protective path must do is part of the machine risk assessment. Torque inhibition can permit coasting, and a tabletop arm can drop a load when torque vanishes. A software flag alone gives no evidence about either outcome.

## Choose interfaces by the information you need

A brushed DC gearmotor can use a compatible drive with a duty-cycle and direction interface. Duty cycle sets a fraction of a switching period, so the relationship to wheel speed depends on supply voltage, load, and feedback. A brushless motor needs a drive that handles commutation, which means switching its phases in sequence. A smart drive may expose a current or velocity target and report limits and faults. For each candidate, read what the target means, how saturation is signaled, what reset does to output, and how communication loss changes drive state. Check operating voltage, continuous and transient current, thermal envelope, and feedback compatibility at the component level.

Incremental quadrature signals encode motion by the order of transitions on two channels. A hardware quadrature counter can accumulate transitions while the CPU handles other work. Record count convention, gear ratio, counter width, and direction per wheel. If an encoder generates 12 quadrature cycles per motor revolution, x4 decoding with a 30:1 reduction gives `12 × 4 × 30 = 1,440` counts per wheel revolution. For `Δn` counts in elapsed seconds `Δt`, speed is `2πΔn / (1,440Δt)`. One count in a 5 ms window represents about `0.87 rad/s`. Longer windows lower the quantization step and add lag. An absolute encoder reports position within its specified range at startup and introduces its own validity, latency, and wrap behavior. Track reboot separately from ordinary counter rollover. [Microchip quadrature decoder data sheet](https://ww1.microchip.com/downloads/en/DeviceDoc/70208B.pdf) · [PID feedback](/notes/pid-feedback/)

| Interface | When it fits | Failure signature and next evidence |
| --- | --- | --- |
| CAN | Several low-rate control devices share a bus. Budget arbitration, payload overhead, and traffic bursts. | Error counts rise, low-priority traffic waits, or a controller enters bus-off and stops participating. Compare device state, frame ages, and application sequence gaps. A recovered interface still needs a fresh command session. |
| UART | A nearby point-to-point peripheral exchanges a modest byte stream. Specify baud and a bounded message format with integrity checks and resynchronization. | A frame error or receive overrun can appear as a broken application message. Compare peripheral error counts with parser rejects and time to resynchronize. |
| Ethernet with IP | The host needs high-bandwidth sensors or structured telemetry. Choose the transport explicitly. | Link up can coexist with socket loss or queue buildup. TCP retransmits and delivers bytes in order, which can delay newer commands behind lost data. UDP can lose or reorder datagrams. Record sequence gaps and receive age at the application boundary. |

For any of these interfaces, a successful send is local evidence. Design feedback that reports which command was accepted and which target was applied. Define a bounded latest-value handoff where superseding commands make sense. Preserve a separate, explicit path for fault and reset events. [Linux SocketCAN](https://docs.kernel.org/networking/can.html) · [Microchip USART characteristics](https://onlinedocs.microchip.com/oxy/GUID-EDB1839B-8CB3-4792-92DA-B3964E0885C3-en-US-5/GUID-D2A30854-6913-4802-9DFE-CD35D2A8A64D.html) · [TCP specification](https://www.rfc-editor.org/rfc/rfc9293.html#section-2.2) · [UDP specification](https://www.rfc-editor.org/rfc/rfc768.html)

## Budget energy and transient load separately

At an illustrative regulated 12 V bus, 4 A average across the drives and 1 A average for compute and sensors sum to 60 W. With 72 Wh usable at the bus under the assumed conditions, `72 Wh / 60 W = 1.2 h` is a rough energy estimate. A separate transient scenario of 6 A per drive plus 1 A of compute asks for 13 A, or 156 W at 12 V. Check duration and repetition of the peaks, battery sag, protection trips, regulator margin, and heat during sustained loads. Check whether braking returns energy to the supply and what the drive and source can absorb. These numbers are arithmetic for a budget review. Component and protection decisions need vendor data, measured loads under an approved plan, and review by the responsible engineers. A reboot counter that increments with each acceleration suggests checking supply and reset evidence before retuning the controller.

## Lab — drive a state machine with events

In firmware, a timer or receive interrupt typically does brief work, such as capturing a timestamp and signaling a task. The task parses data, maintains state, and publishes telemetry. Avoid an unbounded queue of motion commands and distinguish a wakeup flag from a count of arrivals. For example, FreeRTOS provides direct task notifications from interrupt context and supports bit flags that can coalesce repeated events. [FreeRTOS task notifications as event flags](https://freertos.org/Documentation/02-Kernel/02-Kernel-features/03-Direct-to-task-notifications/04-As-event-group)

Save the following as `embedded_events.py` and run `python embedded_events.py`. All timestamps are simulated receiver-local milliseconds. An explicit arm event establishes a session and starts its initial lease with output zero. A valid increasing sequence renews the lease. At exactly 50 ms of age, expiry takes precedence over any event. The scalar output is one modeled wheel target. A real transport also needs a strategy for delayed but increasing commands, such as a bounded transfer path with source-age validation in a known clock domain.

```python
LEASE_MS = 50
events = {
    0: ("arm", 1, 0, 0.0),
    5: ("command", 1, 1, 2.8),
    25: ("command", 1, 2, 2.8),
    45: ("command", 1, 2, 7.0),  # Duplicate sequence.
    80: ("command", 1, 3, 2.8),  # Command after expiry.
}
session = last_valid_ms = None
sequence, target = 0, 0.0

for now_ms in range(0, 91, 5):
    if session is not None and now_ms - last_valid_ms >= LEASE_MS:
        session, target = None, 0.0
        print(f"{now_ms:2} ms expired, target={target:.1f} rad/s")
    if now_ms not in events:
        continue
    kind, epoch, seq, requested = events[now_ms]
    if kind == "arm" and session is None:
        session, sequence, last_valid_ms = epoch, 0, now_ms
        print(f"{now_ms:2} ms armed with target zero")
    elif kind == "command" and epoch == session and seq > sequence and abs(requested) <= 8.0:
        sequence, target, last_valid_ms = seq, requested, now_ms
        print(f"{now_ms:2} ms accepted seq={seq}, target={target:.1f} rad/s")
    else:
        print(f"{now_ms:2} ms rejected seq={seq}, target={target:.1f} rad/s")
```

Expect acceptance at 5 and 25 ms, a duplicate rejection at 45 ms, expiry at 75 ms, and rejection at 80 ms. Change the 45 ms event to sequence 3 and add ticks through 100 ms. The expiry moves to 95 ms because only the admissible event renewed the lease. If the duplicate renews the lease, inspect where you write the last-valid timestamp. The model checks one synthetic event per tick and records target state in memory. It measures neither firmware response time nor stopping distance. On hardware, the protective path and safe recovery procedure require commissioning evidence. [Commissioning and diagnostics](/notes/commissioning-and-diagnostics/)

## Exercises

**1. Select a speed estimator.** At a steady `0.20 rad/s`, what does the 5 ms count-difference estimator see? Propose a test for a 50 ms alternative.

<details>
<summary>Solution</summary>

The expected count increment is about 0.23 per 5 ms, producing mostly zeros interrupted by one-count spikes near `0.87 rad/s`. A 50 ms window has a `0.087 rad/s` step. Replay quantized counts from a constant-speed ramp followed by a reversal. Compare steady error and how long the estimate takes to show the reversal. Choose a window using both results.

</details>

**2. Review a reconnect.** After expiry, a transport retry delivers an old session's command just after the operator authorizes a new run. How would you make the replay diagnostic?

<details>
<summary>Solution</summary>

Add `(85, arm session 2)` and `(90, command session 1, sequence 99)` at the corresponding dictionary keys using the existing event tuple format. Check that output remains zero and the last accepted time stays at 85 ms. Add a new session 2 command at 95 ms with a longer tick range to show legitimate recovery. In a real system, require unambiguous session identity across resets and supervise the explicit rearm decision.

</details>

## Summary

Assign sensing, control, supervision, and power responsibilities according to their timing and failure behavior. Write down units and limits at every boundary. Verify loss and recovery with an event trace that distinguishes valid receipt, rejected traffic, and expired output. Carry the timing assumptions into the [next lecture](/notes/real-time-and-cpp/).
