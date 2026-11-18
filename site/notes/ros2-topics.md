---
title: ROS 2 nodes and topics
topic: ROS 2
order: "04"
description: Trace a stream of typed messages from a publisher to its subscribers.
prerequisites: "For the lab: a sourced ROS 2 Jazzy shell. Read the design sections without ROS."
minutes: 40
---

## Why split one robot program into nodes?

A simulator can compute readings, draw the scene, and control the robot inside a single process. Why move readings to a message bus? Because a visualization tool, an experiment recorder, and a controller have different lifetimes and failure modes. You should be able to add a recorder or replace a display without editing the sensor producer. The price is that names, schemas, delivery, and timestamps become explicit interfaces rather than implicit function arguments.

Consider a virtual range sensor. It may run at 10 Hz even when the visualization is paused. If the display pulls data by calling a function inside the simulator process, it is coupled to that process and its implementation. If it subscribes, it can run on its own schedule. In exchange it needs a clear answer to, “Which readings can I miss? How stale is too stale?”

## The idea

A ROS 2 **node** is a unit of computation. A **topic** is a named channel for messages of a specific type. A publisher sends messages to a topic without naming the consuming nodes. Multiple subscribers can observe the same stream, provided their communication settings are compatible.

```text
 simulator node ── publishes ──▶ /scan : sensor_msgs/msg/LaserScan
                                    ├─▶ visualization
                                    ├─▶ logger
                                    └─▶ motion planner (if explicitly wired)
```

A topic is not a shared Python object or necessarily a central queue. Nodes discover endpoints through their middleware configuration. The name and type identify a compatible candidate; Quality of Service (QoS) describes delivery expectations. The application still needs semantics. `LaserScan`, for example, includes range values, angular information, and a header; “array of floats” would not tell you how to turn an index into a direction.

Topic-oriented design fits repeating independent observations. A command with a required acknowledgment needs explicit semantics. A synchronous request for a calibration ID fits a service better than polling a data topic. A long-running simulated grasp with feedback and a result fits an action. The [communication lecture](/notes/ros2-communication/) builds those distinctions and intentionally breaks a QoS match.

## Development walkthrough: test the graph with a synthetic producer

The first milestone is to observe a message, not to bring up a robot or RTX simulator. On Ubuntu 24.04 with ROS 2 Jazzy installed, use two Bash terminals isolated from physical robots. The same setup must be run in each terminal. If Jazzy is not installed, follow the [workspace chapter](/notes/ros2-workspaces/) and return here.

```bash
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DOMAIN_ID=72 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
unset ROS_STATIC_PEERS
```

Choose an unused local domain if 72 is occupied; apply that choice to both terminals. In terminal A run this producer. The toy payload is deliberately a string. It is a transport probe, not a proposed scanner schema.

```bash
ros2 topic pub --rate 2 /study/sample std_msgs/msg/String '{data: synthetic}'
```

In B, inspect the interface and then observe the stream:

```bash
ros2 interface show std_msgs/msg/String
ros2 topic list -t
ros2 topic info -v /study/sample
timeout 6s ros2 topic echo /study/sample std_msgs/msg/String --once
```

Expect one publisher and a received `data: synthetic`. Start a second echo in a third shell with the same setup. Both echoes can receive independently; the first does not remove the message from a shared queue. Stop terminal A. An echo started afterward does not get a new sample merely because it knows the message type. Wait for the timeout rather than mistaking an idle subscription for a crash.

Now run with a different domain in terminal B for just one command. If terminal A is actively publishing in domain 72, B should receive nothing in domain 73. Switch B back to prove the publisher and schema did not change. A matching domain is a discovery prerequisite in this experiment, not an authorization mechanism.

```bash
ROS_DOMAIN_ID=73 timeout 6s ros2 topic echo /study/sample std_msgs/msg/String --once
```

The probe is useful because it isolates graph configuration from sensor code. If it works and `/scan` does not, change one layer at a time. Check whether the simulator is playing and offering a publisher. Then inspect message type and QoS. Finally check capture time and frame even after samples arrive. A successful echo proves delivery to that echo, not validity for another consumer.

## Worked example

Suppose a simulator publishes a virtual range sensor on `/scan`. On a terminal already configured for the simulator's ROS 2 environment, inspect the topic without sending a command to a robot:

```sh
ros2 topic list -t
ros2 topic info -v /scan
ros2 topic echo /scan --once
```

The first command lists visible topics and their types. The second shows endpoints and their Quality of Service (QoS) settings. The last waits for one message. If you don't have a simulator or publisher sending on `/scan`, there will be no scan to print.

If a topic is visible but nothing arrives, check that the publisher is actively sending, the topic name and message type match, and the subscriber's requested QoS is compatible with the publisher's offered QoS.

If `/scan` arrives, pick one sample and inspect the header, angle increment, valid range limits, and array length. A reading at index 5 corresponds to `angle_min + 5 × angle_increment`, not an arbitrary angle. The angle and distance then describe a point in the sensor's frame; using it in the base frame requires transform data at the scan time. This progression separates transport, schema, geometry, and perception rather than trying to debug all four from a blank display.

## Try it

A visualization node and a logger both need the same simulated scan stream. Should you create a second topic just for the logger?

<details>
<summary>Check your answer</summary>
<p>No. Both nodes can subscribe to /scan. Each subscription needs a compatible message type and QoS.</p>
</details>

## Transfer exercise: received but unusable

A scan arrives at the expected rate, but the display paints an obstacle behind the robot while the robot is stationary. Would you start by increasing the publish rate?

<details>
<summary>Check your diagnostic plan</summary>
<p>No. A regular receive rate establishes transport. Verify which scan angle corresponds to straight ahead, inspect the header's frame ID, then check the sensor-to-base rotation using a known obstacle. If the error appears only while moving, also compare acquisition and transform time.</p>
</details>

## What to carry forward

- Separate the producer from independent consumers, but make types, timing, and delivery preferences explicit.
- Use a synthetic node to prove graph plumbing before adding the simulator.
- Use received messages as evidence of transfer. Validate frame, units and freshness separately.

## Read next

- [ROS 2 Jazzy: Understanding topics](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html)
- [Jazzy LaserScan message definition](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/LaserScan.msg)
