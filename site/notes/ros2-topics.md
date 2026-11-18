---
title: ROS 2 nodes and topics
topic: ROS 2
order: "04"
description: Trace a stream of typed messages from a publisher to its subscribers.
---

## The idea

A ROS 2 **node** is a unit of computation. A **topic** is a named channel for messages of a specific type. A publisher sends messages to a topic without naming the consuming nodes. Multiple subscribers can observe the same stream, provided their communication settings are compatible.

## Worked example

Suppose a simulator publishes a virtual range sensor on `/scan`. On a terminal already configured for the simulator's ROS 2 environment, inspect the topic without sending a command to a robot:

```sh
ros2 topic list -t
ros2 topic info -v /scan
ros2 topic echo /scan --once
```

The first command lists visible topics and their types. The second shows endpoints and their Quality of Service (QoS) settings. The last waits for one message. If you don't have a simulator or publisher sending on `/scan`, there will be no scan to print.

If a topic is visible but nothing arrives, check that the publisher is actively sending, the topic name and message type match, and the subscriber's requested QoS is compatible with the publisher's offered QoS.

## Try it

A visualization node and a logger both need the same simulated scan stream. Should you create a second topic just for the logger?

<details>
<summary>Check your answer</summary>
<p>No. Both nodes can subscribe to /scan. Each subscription needs a compatible message type and QoS.</p>
</details>

## Read next

- [ROS 2 Jazzy: Understanding topics](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html)
