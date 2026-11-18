---
title: "Keep robot frames and clocks consistent"
topic: "ROS 2"
order: "12"
description: "Build a small TF tree and define the frame, unit, and timestamp contract at a simulator bridge."
prerequisites: "Jazzy workspace, typed topics, and basic coordinate transforms."
minutes: 45
---

## Separate geometry, state, and time

URDF describes the robot's kinematic model. Links name rigid bodies and joints connect parent and child links with an origin, axis, and allowed motion. A `sensor_msgs/msg/JointState` supplies measured or simulated values for named joints at a time. Its `name[i]` corresponds to `position[i]`, with radians for revolute joints and meters for prismatic joints. `robot_state_publisher` combines the model and joint values to publish fixed edges on `/tf_static` and moving edges on `/tf`. Give each child frame one parent and one publishing authority. [Jazzy robot_state_publisher](https://raw.githubusercontent.com/ros/robot_state_publisher/jazzy/README.md) · [JointState definition](https://raw.githubusercontent.com/ros2/common_interfaces/jazzy/sensor_msgs/msg/JointState.msg)

![TF tree with a moving base_link to wrist_link edge on /tf and a fixed wrist_link to tool_link edge on /tf_static. Rotating the wrist changes the tool pose in the base frame.](/assets/ros2-tf-chain.svg)

Read `lookup_transform(target, source, time)` as “express data from source in target at time.” This partial Python example assumes a populated tf2 `Buffer` named `buffer` and a stamped tool-frame message named `observation`. It retrieves the transform for use in a later coordinate conversion.

```python
from rclpy.time import Time

transform = buffer.lookup_transform(
    'base_link',
    observation.header.frame_id,
    Time.from_msg(observation.header.stamp),
)
```

Zero requests the latest available transform. A moving wrist makes that a poor substitute for the observation's acquisition time. If lookup extrapolates, compare the stamp to the transform cache interval. Check for stale messages, transforms that have yet to arrive, or mixed clock domains. With `use_sim_time` true on a node, its ROS clock follows `/clock` and starts uninitialized until clock messages arrive. Test pauses and backward jumps. Clear or reset your own time-indexed state on a rewind. [Jazzy tf2 buffer](https://raw.githubusercontent.com/ros2/geometry2/jazzy/tf2_ros_py/tf2_ros/buffer.py) · [ROS clock design](https://design.ros2.org/articles/clock_and_time.html)

## Lab — predict a composed transform

Use the earlier [Jazzy terminal setup](/notes/ros2-workspaces/) and keep system time for this lab. In Ubuntu, install `sudo apt install ros-jazzy-robot-state-publisher ros-jazzy-tf2-ros` if needed. Save this complete URDF as `~/robo_ws/tabletop.urdf`.

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

Run the following in three separate terminals. The joint publisher stamps each synthetic sample using its ROS clock. The commands exercise kinematics without simulating physics or commanding hardware.

```bash
# A: load the XML into the robot_description string parameter
ros2 run robot_state_publisher robot_state_publisher --ros-args \
  -p "robot_description:=$(tr '\n' ' ' < "$HOME/robo_ws/tabletop.urdf")"

# B: turn the wrist by a quarter turn around +Z
ros2 topic pub --rate 2 /joint_states sensor_msgs/msg/JointState \
  '{header: auto, name: [elbow_joint], position: [1.57079632679]}'

# C: inspect the tool origin expressed in the base frame
ros2 run tf2_ros tf2_echo base_link tool_link
```

Expect translation near `[0, 0.2, 0]` meters and yaw near +90 degrees. If the fixed wrist-to-tool segment works alone, inspect `/joint_states` for the correct joint name and a fresh stamp before debugging the moving edge. Stop all three processes after the check. [Jazzy topic publisher source](https://raw.githubusercontent.com/ros2/ros2cli/jazzy/ros2topic/ros2topic/verb/pub.py)

## Write the simulator bridge contract

For the [tabletop capstone](/notes/capstone-tabletop/), specify each bridge interface before connecting software.

| Field | Record and verify |
| --- | --- |
| Schema and direction | Topic/type, publisher, expected rate, and QoS |
| Geometry | Frame IDs, axes, units, joint names, and quaternion order |
| Time | Stamp at acquisition or simulation step, choose one /clock authority, and define reset behavior |

Test the mapping with a known 90-degree joint movement and an observation transformed at its original stamp. Define the separate episode export mapping before offline imitation evaluation. [ROS coordinate conventions](https://www.ros.org/reps/rep-0103.html)

## Self-check

Why does a fixed 0.2 m tool offset along wrist X show up along base Y?

<details>
<summary>Check your answer</summary>
<p>The moving edge rotates the wrist by +90 degrees about base Z. The composed base-from-tool transform rotates the wrist's local +X offset into base +Y.</p>
</details>

Next, preserve these contracts in [ROS 2 bags and testing](/notes/ros2-bags-and-testing/).
