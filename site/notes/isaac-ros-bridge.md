---
title: Read simulated sensors through the ROS 2 bridge
topic: Isaac Sim
order: "22"
description: Bring up a ROS 2 bridge and use clock, frame, and delivery checks to explain missing or slow sensor data.
prerequisites: Isaac Sim 6.1.0 on Ubuntu 24.04 and basic ROS 2 topics
minutes: 50
---

## Time, frames, and delivery

The Isaac Sim ROS 2 Bridge turns simulation state into typed ROS messages and can pass incoming ROS commands back to the simulator. This lab observes publishers in a simulation-only ROS domain. A sensor message is useful when its consumer can answer three questions. When was the sample taken? In which frame? Did the transport deliver it in time? [ROS 2 nodes and topics](/notes/ros2-topics/)

| Contract | What to check |
| --- | --- |
| Time | Use one `/clock` publisher for the simulation. Set `use_sim_time` on consumers such as RViz that should follow it. Keep sensor and transform timestamps in the same time domain. |
| Frames | TF provides transforms between named frames at a given time. Use the sensor message's `header.frame_id` and follow the TF chain to the consumer's fixed frame. Dynamic transforms use `/tf`. Static transforms are normally sent on `/tf_static`. |
| Delivery | Quality of Service (QoS) controls properties such as reliability, durability, and queue depth. A reliable subscription cannot receive from a publisher offering only best effort. Sensor streams commonly favor recent samples. |

For a custom stage in 6.1.0, put the camera or articulation root in the **Isaac Compute Transform Tree** node's `targetPrims`. That node computes transforms for **ROS 2 Publish Transform Tree** to publish. See the tutorial for the execution and simulation-time connections. For a camera, check that the published frame uses the expected optical axes as well as the expected name. [NVIDIA TF graph](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_tf.html) · [ROS 2 Jazzy QoS](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Quality-of-Service-Settings.rst)

## Lab · inspect NVIDIA's multi-sensor example

1. On the same Ubuntu 24.04 host, install ROS 2 Jazzy using the **Default ROS Interfaces** path. Use Fast DDS. Choose an unused simulation-only domain (37 below) and keep the host off physical robot networks. Run the following in a fresh Bash terminal in the Isaac Sim installation directory. In **Window → Extensions**, confirm that `isaacsim.ros2.bridge` is enabled. [NVIDIA 6.1.0 bridge setup](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_ros.html)

   ```bash
   source /opt/ros/jazzy/setup.bash
   export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
   export ROS_DOMAIN_ID=37
   export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
   unset ROS_STATIC_PEERS
   ./isaac-sim.sh
   ```

2. In the Isaac Sim Content Browser, open **Isaac Sim → Samples → ROS2 → Scenario → `turtlebot_tutorial_multi_sensor_publish_rates.usd`**. This model is a sensor fixture for the lab. Before pressing **Play**, run the official tutorial's **Setting the Simulation Rate** snippet in the Script Editor with `target_hz = 60`. It sets the physics and playback rates together. Then press **Play**. [NVIDIA sample scene and rate setup](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_publish_rate.html#setting-the-simulation-rate)
3. In a second Bash terminal, inspect the published messages. These are runnable commands. Let `hz` collect several samples, then stop it with Ctrl+C.

   ```bash
   source /opt/ros/jazzy/setup.bash
   export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
   export ROS_DOMAIN_ID=37
   export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
   unset ROS_STATIC_PEERS
   ros2 topic list -t
   ros2 topic info /clock -v
   ros2 topic echo /clock --once
   ros2 topic echo /tf --once
   ros2 topic echo /camera_1/rgb/camera_info --once
   ros2 topic info /camera_1/rgb/image_raw -v
   ros2 topic hz /camera_1/rgb/image_raw
   ```

**Checkpoint.** Check for one clock publisher and advancing timestamps while playing. Pause and verify that simulation time stops advancing. Compare the camera frame in `CameraInfo` with the transform tree. One `/tf` message may contain only part of that tree. In RViz, set `use_sim_time` to true and choose a fixed frame with a path to the sensor. [NVIDIA clock tutorial](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_clock.html)

**Rate experiment.** The sample targets 15 camera captures per simulated second. Use `ros2 topic echo /camera_1/rgb/camera_info --field header` to collect stamps. While stopped, change `/World/Camera_1`'s `omni:sensor:tickRate` from 15 to 10 and replay. Check whether consecutive camera stamps move from about 67 ms apart to 100 ms apart. `ros2 topic hz` measures arrivals in wall time. If the simulation advances half a simulated second per wall second, 10 captures per simulated second yield about five arrivals per wall second before transport losses. Leave the older camera helper's deprecated frame-skip setting at zero. [NVIDIA sensor rate controls](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_publish_rate.html#rtx-sensors)

**Diagnostics.** If the topic list is empty, check Play, bridge startup, domain ID, and middleware. If an image topic exists but the subscriber gets nothing, inspect offered and requested QoS and confirm the render product is enabled. If images arrive but RViz reports a transform error, compare the frame chain and timestamp domains before changing transport settings.

## Self-check

The image topic is visible and `ros2 topic hz` shows arrivals, but RViz reports that the image's frame is unknown. What do you inspect first?

<details>
<summary>Check your answer</summary>
<p>Read the image's frame ID and trace it to the fixed frame. If that path exists, check whether TF covers the image timestamp and whether RViz follows the same clock.</p>
</details>

Continue to [simulation experiments](/notes/isaac-experiments/) and use these checks when attaching a camera to the capstone arm.
