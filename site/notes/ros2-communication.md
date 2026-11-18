---
title: "Choose and debug ROS 2 communication"
topic: "ROS 2"
order: "11"
description: "Choose topics, services, or actions and diagnose why discovered endpoints fail to exchange data."
prerequisites: "A working Jazzy workspace and the heartbeat lab."
minutes: 35
---

## Read the graph as a set of contracts

A process can host one or more **nodes**. Each node exposes endpoints such as publishers, subscriptions, or service clients. ROS 2 discovery lets participants learn which endpoints exist. A name like `/tabletop/heartbeat` identifies a channel, and the type `std_msgs/msg/String` describes its payload. Use `ros2 interface show std_msgs/msg/String` to see the generated interface's fields. A real observation type also needs documented semantics such as units and timestamp source. The schema alone cannot tell a subscriber whether a number means radians or degrees.

| What the caller needs | Interface | Tabletop example |
| --- | --- | --- |
| Observe a stream with zero or more independent consumers | Topic with a message type (`.msg`) | Feed joint readings to visualization and to a recorder |
| Get a bounded request/response from a server | Service with request and response types (`.srv`) | Query the simulator for its current scenario ID |
| Track a long-running goal with feedback, cancellation, and a result | Action with goal, result, and feedback types (`.action`) | Request a simulated pick-and-place and observe progress |

An action server chooses whether to accept a goal or a cancellation request. A client should distinguish goal acceptance from completion and account for rejected, aborted, or canceled goals. If you published a pick request on a bare topic, you would need to define that goal lifecycle yourself. [ROS 2 interfaces](https://docs.ros.org/en/jazzy/Concepts/Basic/About-Interfaces.html) · [ROS 2 action design](https://design.ros2.org/articles/actions.html)

## Reason about delivery before increasing queue depth

Quality of Service (QoS) describes what a publisher **offers** and what each subscriber **requests**. A reliable publisher can satisfy a best-effort subscriber, but a best-effort publisher cannot satisfy a reliable subscriber. Volatile durability is appropriate for streams where late joiners can wait for the next sample. Transient local durability lets a late joiner request retained samples while the publisher is present. For historical delivery, both endpoints need transient local durability. With keep-last history, depth limits how many samples an endpoint keeps. A larger queue cannot repair incompatibility and may let a slow consumer work through more stale readings. For a high-rate camera, decide how much a missing frame matters versus how much a stale frame matters. [Jazzy QoS compatibility tables](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html)

## Lab — make a visible topic fail

Open two Bash terminals with the workspace and local discovery settings. Start the synthetic stream in terminal A. [Terminal setup](/notes/ros2-workspaces/)

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
ros2 topic echo /tabletop/sample std_msgs/msg/String \
  --once --qos-reliability best_effort
```

Expect a visible publisher offering best effort, an incompatible reliable echo with no sample, and then `data: preview` from the compatible echo. If the publisher is absent from the graph, check the two shells' domain and discovery settings before interpreting QoS. If the last echo waits, verify terminal A is still publishing and the topic and type match. Stop the publisher with Ctrl+C. All commands use synthetic data and send no motion goals. [Jazzy topic CLI source](https://github.com/ros2/ros2cli/tree/jazzy/ros2topic/ros2topic/verb)

## When the endpoint matches and the callback stalls

The executor runs ready callbacks. On a single-threaded executor, slow work in one callback delays timers and subscriptions on that executor. A callback that synchronously calls a service can deadlock while waiting for a result whose completion callback needs the executor. Adding executor threads alone can leave the same deadlock if the caller and client share the default mutually exclusive callback group. In Python, use `call_async`, return from the initiating callback, and handle the future when it completes. For heavy ML inference, bound pending work and measure both processing time and the age of consumed observations. A responsive callback and fresh data are separate tests. [Jazzy callback-group guide](https://docs.ros.org/en/jazzy/How-To-Guides/Using-callback-groups.html)

## Self-check

Your reliable camera subscriber sees a best-effort camera publisher in the graph. A separate service callback stops producing timer ticks after a synchronous call. Which changes address the two symptoms?

<details>
<summary>Check your answer</summary>
<p>Request best effort on the subscriber if the application tolerates loss, or configure the publisher to offer reliable delivery. For the service, return control to the executor after sending an asynchronous request and handle completion separately.</p>
</details>

Next, attach meaning to a stream with [ROS 2 frames and time](/notes/ros2-frames-and-time/).
