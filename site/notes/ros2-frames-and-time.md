---
title: "Keep robot frames and clocks consistent"
topic: "ROS 2"
order: "12"
description: "Build a small TF tree and define the frame, unit, and timestamp contract at a simulator bridge."
prerequisites: "Jazzy workspace, typed topics, and basic coordinate transforms."
minutes: 45
---

## Predict where the tool tip should be

A detection says that a point is 20 cm ahead. Ahead of the camera, the wrist, or the robot base? If the wrist turned after exposure, which orientation should the controller use? A graph can deliver every observation on time and still yield a systematically wrong target. Build a three-frame model whose expected coordinates you can compute by hand. Make its tool origin move from `[0.2, 0, 0]` to `[0, 0.2, 0]` meters in the base frame with a single joint change. Then reason about how you would reproduce either answer from a stamped observation after the wrist has moved.

## Separate geometry, state, and time

URDF describes the robot's kinematic model. Links name rigid bodies. Each joint specifies its parent and child, the joint pose in its parent at zero displacement, and, for moving joints, the axis in the joint frame. A `sensor_msgs/msg/JointState` supplies values for named joints at a time. Its `name[i]` corresponds to `position[i]`, with radians for a rotating joint and meters for a prismatic joint. Map hardware or simulator names explicitly. Array order alone is a poor identifier once another producer or a partial joint update enters the graph.

`robot_state_publisher` combines the model and joint values to publish fixed edges on `/tf_static` and moving edges on `/tf`. Give each child one parent and each edge one intended publishing authority. A simulator can publish the transforms directly, which is useful if it owns geometry that does not come from a URDF. Computing the robot's transforms from its model and joint state gives other tools a shared kinematic description. Pick an authority for each edge before using both approaches in one graph. This lab uses one model and one joint publisher, with no root motion or physics. [Jazzy robot_state_publisher](https://raw.githubusercontent.com/ros/robot_state_publisher/jazzy/README.md) · [JointState definition](https://raw.githubusercontent.com/ros2/common_interfaces/jazzy/sensor_msgs/msg/JointState.msg)

![TF tree with a moving base_link to wrist_link edge on /tf and a fixed wrist_link to tool_link edge on /tf_static. Rotating the wrist changes the tool pose in the base frame.](/assets/ros2-tf-chain.svg)

The diagram shows two different inputs to the composition. The tool offset is always 0.2 m along wrist +X. The moving edge tells you which way wrist +X points in the base. A positive quarter turn about +Z rotates +X toward +Y. For a tool point also 0.1 m along tool +X, first add the mount offset in wrist coordinates to get `[0.3, 0, 0]`, then rotate to `[0, 0.3, 0]` in base coordinates. Reversing the transform or adding the mount offset in the base frame gives a different answer.

## Ask the buffer a time-specific question

Read `lookup_transform(target, source, time)` as “express data from source in target at time.” This excerpt assumes a running tf2 listener has populated a `Buffer` named `buffer`, and `observation` is a stamped tool-frame message. The lookup retrieves the transform. The caller then applies it to the observation's coordinates with a geometry helper appropriate to the message type.

```python
from rclpy.time import Time

stamp = Time.from_msg(observation.header.stamp)
if stamp.nanoseconds == 0:
    raise ValueError('the observation contract requires a nonzero stamp')
transform = buffer.lookup_transform(
    'base_link',
    observation.header.frame_id,
    stamp,
)
```

Zero requests the latest available transform for the chain. This observation contract rejects zero so an uninitialized stamp cannot silently trigger that behavior. Here is an illustrative history, with the observer running after all three transforms have arrived:

```text
ROS time (s)      10.00           10.10             10.20
wrist yaw         0 deg          +45 deg           +90 deg
                  ^                                   ^
              image taken                       latest TF now

tool origin for image stamp 10.00 -> [+0.200, 0,      0] m
tool origin for latest lookup    -> [0,      +0.200, 0] m
image taken at 10.05 instead     -> [+0.185, +0.077, 0] m
```

The first two results differ by about 28 cm even though both lookups can succeed. The intermediate example uses 22.5 degrees: with bracketing samples on the same dynamic edge, tf2 interpolates translation and orientation. It does not infer the wrist's future motion. If the stamp is newer than available transforms, allow a short, bounded wait for TF to arrive. Let the listener's callbacks run while you wait. In a single-threaded executor, blocking a subscription inside a lookup can prevent those callbacks from filling the buffer. Queue a small number of observations and retry outside the receiving callback, or use asynchronous transform waiting. If the stamp predates the cache, inspect processing age, cache history, and clock agreement. A missing frame or disconnected tree calls for a topology check before either timing fix. [Jazzy tf2 cache](https://raw.githubusercontent.com/ros2/geometry2/jazzy/tf2/src/cache.cpp) · [Jazzy tf2 buffer](https://raw.githubusercontent.com/ros2/geometry2/jazzy/tf2_ros_py/tf2_ros/buffer.py)

With `use_sim_time` true on a node, its ROS clock follows `/clock`. Treat zero before clock initialization as a startup condition. Use ROS time for acquisition, transform matching, and measurement age. Use a monotonic wall-time deadline for waiting on startup, so a paused simulator cannot prevent a test from timing out. An epoch-sized difference between observations and TF often indicates mixed system and sim time. During a reset, clear application queues and cached episode state and wait for the new interval to populate before using observations again. Test pauses and backward jumps explicitly. [ROS clock design](https://design.ros2.org/articles/clock_and_time.html)

## Lab — predict a composed transform

Source `~/robo_ws/lab-env.bash` in three fresh shells and keep system time throughout this lab. On Ubuntu 24.04, install `ros-jazzy-robot-state-publisher` and `ros-jazzy-tf2-ros` if needed. Save this complete URDF as `~/robo_ws/tabletop.urdf`. The wrist starts coincident with the base, so the tool mount is the only translation. [Jazzy terminal setup](/notes/ros2-workspaces/)

```xml
<robot name="tabletop_demo">
  <link name="base_link"/>
  <link name="wrist_link"/>
  <link name="tool_link"/>
  <joint name="elbow_joint" type="continuous">
    <parent link="base_link"/>
    <child link="wrist_link"/>
    <axis xyz="0 0 1"/>
  </joint>
  <joint name="tool_mount" type="fixed">
    <parent link="wrist_link"/>
    <child link="tool_link"/>
    <origin xyz="0.2 0 0"/>
  </joint>
</robot>
```

If `check_urdf` is available (`liburdfdom-tools` on Ubuntu 24.04), run `check_urdf ~/robo_ws/tabletop.urdf`. Verify that the parser sees `base_link` as root and the wrist and tool as successive children. A parsed tree can still have a reversed joint axis or a surveyed offset entered in centimeters. Use the numeric checkpoint to catch those bugs. [Ubuntu Noble URDF tools](https://packages.ubuntu.com/noble/liburdfdom-tools)

Run the following in three separate terminals. The joint publisher stamps each synthetic sample using its ROS clock. The commands exercise kinematics without simulating physics or commanding hardware.

```bash
# A: load the XML into the robot_description string parameter
ros2 run robot_state_publisher robot_state_publisher --ros-args \
  -p "robot_description:=$(tr '\n' ' ' < "$HOME/robo_ws/tabletop.urdf")"

# B: start with the joint at zero
ros2 topic pub --rate 2 /joint_states sensor_msgs/msg/JointState \
  '{header: auto, name: [elbow_joint], position: [0.0]}'

# C: inspect the tool origin expressed in the base frame
ros2 run tf2_ros tf2_echo base_link tool_link
```

At zero expect translation near `[0.2, 0, 0]` m and yaw near zero. Stop B and repeat its command with `position: [1.57079632679]`, leaving A and C running. Expect translation near `[0, 0.2, 0]` m and yaw near +90 degrees. Record what C prints for each setting, including the stamp. `tf2_echo` as used here reports the latest available transform. Its result verifies the two steady configurations. The time-specific lookup above exercises a different question.

If C never resolves the full chain, probe the mount alone with `ros2 run tf2_ros tf2_echo wrist_link tool_link`. You can inspect the fixed edge after startup with `ros2 topic echo /tf_static --qos-durability transient_local --once`. If the mount works, inspect `ros2 topic echo /joint_states --once` in a separate shell for a fresh stamp, exact joint name, and radian value. Then check `/tf` for a base-to-wrist edge. If the chain resolves but a quarter turn lands on base `-Y`, start with the sign of the joint axis and the direction of the transform query. If it lands far from the base, check the offset and units. Each probe should narrow the set of explanations before you edit the model. Stop all three processes after the check. [Jazzy topic publisher source](https://raw.githubusercontent.com/ros2/ros2cli/jazzy/ros2topic/ros2topic/verb/pub.py) · [Jazzy tf2_echo source](https://raw.githubusercontent.com/ros2/geometry2/jazzy/tf2_ros/src/tf2_echo.cpp)

## Write the simulator bridge contract

For the [tabletop capstone](/notes/capstone-tabletop/), specify each bridge interface before connecting software.

| Field | Record and verify |
| --- | --- |
| Schema and direction | Topic/type, publisher, expected rate, and QoS |
| Geometry | Frame IDs, axes, units, joint names, and quaternion order |
| Time | Stamp at acquisition or simulation step, choose one `/clock` authority, and define reset behavior |

For the Isaac Sim 6.1.0 Franka bridge, run the known-angle test against the actual published axes before using a detection to choose a command. Verify camera optical axes separately, since an optical frame uses +Z forward, +X right, and +Y down. Stamp the observation when acquired, match TF at that stamp, and pair the observation with the action chosen afterward. Retain both times for later checks. The LeRobot 0.4.3 PushT lab in Python 3.12 is a separate task. Sharing coordinates through ROS does not supply the explicit adapter that would be needed to export the Franka demonstrations to a learning environment. [ROS coordinate conventions](https://www.ros.org/reps/rep-0103.html)

## Exercises

**1. Predict a new orientation.** Change the wrist command to `-1.57079632679` rad. Before running it, predict the tool origin in the base frame. Then predict the coordinates of a point 0.1 m along tool +X.

<details>
<summary>Solution</summary>
<p>The negative quarter turn maps wrist +X to base −Y. The origin is at [0, −0.2, 0] m. The point is at [0, −0.3, 0] m. Check the origin with tf2_echo, then apply the same transform to the point rather than reading translation as point coordinates.</p>
</details>

**2. Debug a capture with two clock domains.** Camera observations carry stamps near 3.5 s after reset. TF is available only at system-epoch stamps. A latest lookup appears to work. What would make an exact-time test pass?

<details>
<summary>Solution</summary>
<p>Verify that both producers use the same acquisition clock and fix the TF producer to stamp from the simulation timeline. Check that sim-time consumers receive the single intended clock, then take a fresh observation after reset and verify that the dynamic TF interval brackets its stamp. A latest lookup skips the time contract and can silently return the pose after the observation.</p>
</details>

## Common misconceptions

- **A valid URDF guarantees correct geometry.** Parsing checks the model structure. Verify signs and magnitudes at known joint values.
- **A static transform makes the composed pose static.** The mount is fixed in its parent. A changing upstream edge changes the pose in the base.
- **Every extrapolation error means the cache is too small.** Compare the requested stamp with both ends of the interval and check the clock domains.

## Summary

Compute an expected pose, verify the static and moving edges separately, and vary one joint to confirm the composition. Before using a point for control, verify that the chain resolves at acquisition time under the intended clock.

Next, preserve these contracts in [ROS 2 bags and testing](/notes/ros2-bags-and-testing/).
