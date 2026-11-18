---
title: "Choose and debug ROS 2 communication"
topic: "ROS 2"
order: "11"
description: "Choose topics, services, or actions and diagnose why discovered endpoints fail to exchange data."
prerequisites: "A working Jazzy workspace and the heartbeat lab."
minutes: 35
---

## Explain a visible topic that delivers nothing

Your simulator's preview topic appears in the ROS graph, but the perception node receives no frames. A restart occasionally seems to help. Before replacing the node, build a two-terminal experiment that makes this symptom predictable. The target is a publisher you can discover in both trials, a subscriber that receives nothing with one explicit QoS setting, and a subscriber that receives a sample when you change just that setting. Then ask what you would measure if samples arrived but processing still fell behind.

## Design the interface around what can go wrong

A process can host several **nodes**. The graph describes the endpoints those nodes expose, including publishers, subscriptions, and service clients. Discovery learns that an endpoint exists. To exchange topic data, endpoints also need the same resolved topic name and message type and compatible QoS. `ros2 interface show std_msgs/msg/String` displays the generated fields. For observations and commands, a type gives clients a common encoding and lets tools introspect fields. Write the semantic contract alongside it: which frame describes the values, what event the stamp refers to, and whether angles are in radians. Two publishers using the same type can still disagree on all three.

| What the caller needs | Interface | Tabletop example |
| --- | --- | --- |
| Observe a stream with zero or more independent consumers | Topic with a message type (`.msg`) | Feed joint readings to visualization and to a recorder |
| Get a short request/response from a server | Service with request and response types (`.srv`) | Query the simulator for its current scenario ID |
| Track a long-running goal with feedback, cancellation, and a result | Action with goal, result, and feedback types (`.action`) | Request a simulated pick-and-place and observe progress |

Use a topic for observations because each consumer can start, stop, and choose its delivery policy independently. Adding a recorder need not change the simulator's application code. There is no application-level acknowledgment that the planner used any particular frame. A service makes sense for a quick snapshot or a bounded query. The API has distinct request and response fields, but the application still needs a timeout policy. After a timed-out state-changing request, you may have an unknown outcome: the server might have acted before the reply was lost or delayed. An automatic retry is easiest to justify for a read or a deliberately idempotent mutation.

A simulated pick may take seconds and stop early. Use an action when the caller must track that lifecycle. The goal could carry the target pose, feedback could report the active phase, and the result could report the terminal status and measured placement error. Handle rejection before polling for a result. Handle cancellation acceptance separately from the resulting terminal state. The server can accept a goal and later abort it. ROS associates those messages with goals and implements the protocol using services and topics underneath. A bare command topic would leave you to design goal identity, status, cancellation, and result correlation. A long synchronous service moves the lifecycle problem into a blocked caller. [ROS 2 interfaces](https://docs.ros.org/en/jazzy/Concepts/Basic/About-Interfaces.html) · [ROS 2 action design](https://design.ros2.org/articles/actions.html)

## Reason about delivery before increasing queue depth

Quality of Service (QoS) describes what a publisher **offers** and what each subscriber **requests**. A reliable publisher can satisfy a best-effort request. A best-effort offer cannot satisfy a reliable request. Volatile durability fits streams where a late joiner can wait for the next sample. Transient local durability lets a live publisher retain samples for late-joining subscriptions that also request transient local durability. A static transform is valuable long after it was published. Yesterday's camera frame is usually irrelevant. Both are topics, with different retention and delivery needs.

With keep-last history, depth limits the number of samples retained at an endpoint. Suppose frames arrive at 30 Hz and one worker needs 80 ms per frame. In this simplified estimate the worker can handle 12.5 frames/s, leaving a deficit of roughly 17.5 frames/s. A queue may absorb a short burst, but sustained overload eventually costs frames, increases age, or creates backpressure depending on the setup. Larger history cannot fix a QoS mismatch. For a preview stream, accepting frame loss and keeping only recent work may be preferable. For a dataset writer that requires a complete sequence, measure loss and provision throughput or throttle the source. Reliable delivery alone does not guarantee every application callback completes on time. [Jazzy QoS compatibility tables](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html)

## Lab — make a visible topic fail

Open two Bash terminals and source `~/robo_ws/lab-env.bash` in both. Start one synthetic publisher in A. Fix the topic name, message type, rate, and payload so the reliability experiment has one independent variable. [Terminal setup](/notes/ros2-workspaces/)

```bash
ros2 topic pub --rate 2 --qos-reliability best_effort \
  /tabletop/sample std_msgs/msg/String '{data: preview}'
```

In terminal B, inspect the graph and try each reliability policy in turn.

```bash
ros2 topic list -t
ros2 topic info -v /tabletop/sample
timeout 5s ros2 topic echo /tabletop/sample std_msgs/msg/String \
  --once --qos-reliability reliable
timeout 5s ros2 topic echo /tabletop/sample std_msgs/msg/String \
  --once --qos-reliability best_effort
```

Expect a visible publisher offering best effort, a reliable echo that times out, and `data: preview` from the best-effort echo. Record the offered policy and the outcome of each echo. Five seconds is a diagnostic budget for a local lab, so also confirm that A was already publishing when you made the comparison. If the publisher is absent, compare domains and discovery settings first. If both attempts hang, verify that A is still sending and that the resolved name and type are right. If both succeed, check for a second publisher before drawing a conclusion.

Iterate once from the other side. Keep B's reliable probe fixed, restart A with `--qos-reliability reliable`, and repeat the probe. Now it should receive `preview`. That isolates the incompatibility to the relationship between the offer and the request. The application requirement decides which endpoint should change in a real system. Stop the publisher with Ctrl+C. [Jazzy topic CLI source](https://github.com/ros2/ros2cli/tree/jazzy/ros2topic/ros2topic/verb)

## When the endpoint matches and the callback stalls

The rclpy executor runs ready work such as a subscription callback, timer, or service response handler. Readiness makes work eligible to run. Thread availability and callback groups decide when it can run. In this illustrative trace the client uses a single executor thread. The server runs in another process.

```text
Elapsed     Client executor                         Server
   0 ms     timer enters, sends request, waits      receives request
   8 ms     still in timer                          sends reply
  10 ms     next timer is due, reply is ready        idle
 100 ms     still waiting for the reply handler     idle

After changing only the client to send-and-return:
   0 ms     timer sends request, returns            receives request
   8 ms     can handle ready reply on arrival       sends reply
  10 ms     eligible to run next timer              idle
```

The first timeline can occur even though the reply reaches the client correctly. The sole executor thread is still occupied by the waiter. In rclpy, entities default to the node's mutually exclusive callback group. Adding threads while keeping both the waiting timer and the client in that group can still block response handling. Separate groups and available threads can allow concurrency, with a cost in shared-state synchronization. Start by avoiding the wait inside the callback. [Jazzy callback-group guide](https://docs.ros.org/en/jazzy/How-To-Guides/Using-callback-groups.html)

Here is the core of a client-node pattern. Assume `self.client` is a `std_srvs/srv/Trigger` client, `Trigger` is imported from `std_srvs.srv`, and `self.pending` starts as `None`. Use a timer to call `poll_server`. This excerpt assumes a single-threaded executor.

```python
def poll_server(self):
    if self.pending is not None or not self.client.service_is_ready():
        return
    self.pending = self.client.call_async(Trigger.Request())
    self.pending.add_done_callback(self.on_reply)


def on_reply(self, future):
    self.pending = None
    try:
        reply = future.result()
    except Exception as exc:
        self.get_logger().error(f'service reply failed: {exc}')
        return
    self.get_logger().info(f'success={reply.success}: {reply.message}')
```

Returning lets response processing proceed. The pending guard keeps a fast timer from flooding a slow service. An application that must recover from a missing reply also needs a deadline, cleanup of the outstanding request, and a policy for an outcome that is unknown. When diagnosing a stall, log monotonic callback entry and exit times and the reply completion. If your expensive operation is ML inference, measure processing duration and the age of the input at use, using its acquisition clock for age. Bound pending work before adding workers. For many preview pipelines, a worker that takes the freshest available frame keeps input age low by dropping superseded work. A separate process can also isolate CPU-bound Python work and provide independent scheduling, at the cost of another data transfer and process to monitor.

## Exercises

**1. Debug two different stalls.** A camera subscriber sees a best-effort publisher and receives no frames. After installing a compatible probe, that probe receives frames, but a timer in the application still stops after requesting a service. Which evidence should trigger each fix?

<details>
<summary>Solution</summary>
<p>Compare the camera offer with the application's request and verify the match with the one-setting echo experiment. For the timer, log request, callback return, and completion. If the executor is stuck inside a synchronous call, send asynchronously and return from the timer so the reply can be dispatched. An independent echo exercises delivery to its own subscription. It says little about the application's executor.</p>
</details>

**2. Design a pick interface.** The operator wants to cancel an in-progress simulated pick, while a visualizer and recorder need every available progress observation. Name the interfaces and say what you would test.

<details>
<summary>Solution</summary>
<p>Use an action for the pick lifecycle. Verify separately that an accepted goal can complete and that a cancel request can reach the appropriate terminal result. If independent consumers need robot observations, publish a typed state topic with documented units and stamps. Test the recorder under load for gaps and select its QoS and source rate accordingly. The action feedback lifecycle covers the goal client, while the observation topic supports independent consumers.</p>
</details>

## Common misconceptions

- **Graph visibility proves delivery.** Check resolved names, types, and both endpoints' policies, then observe a sample.
- **A deeper queue fixes a slow callback.** It gives work somewhere to wait. Compare measured sample age and processing capacity before increasing depth.
- **A returned goal handle proves success.** Inspect acceptance and then the terminal result. They answer different questions.

## Summary

Choose the interface based on what the caller needs to observe or control. Prove discovery, matching, and delivery separately. Once messages arrive, use callback timing and input age to distinguish an executor stall from a throughput problem.

Next, attach meaning to a stream with [ROS 2 frames and time](/notes/ros2-frames-and-time/).
