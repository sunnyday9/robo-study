---
title: Read simulated sensors through the ROS 2 bridge
topic: Isaac Sim
order: "22"
description: Bring up a ROS 2 bridge and use clock, frame, and delivery checks to explain missing or slow sensor data.
prerequisites: Isaac Sim 6.1.0 on Ubuntu 24.04 and basic ROS 2 topics
minutes: 50
---

## Make a camera sample usable outside the simulator

You can see a camera view in Isaac Sim and still have an unusable observation in a ROS program. The program might receive nothing, receive a frame with an incompatible timestamp, or receive good pixels that it cannot associate with a robot pose. Before wiring a policy to the simulator, prove that an external Jazzy process sees one advancing simulation clock, receives a stamped camera sample, and can interpret the frame at the sample time. Then explain why the measured arrival cadence agrees with or differs from the configured capture cadence.

The bridge translates selected simulation state and sensor products into typed ROS messages. It can also translate incoming commands, which this lab leaves unconnected. Keeping the lab on a local simulation-only domain makes the bridge's publication path easier to debug and gives you a known observation stream before adding any feedback over ROS. [ROS 2 nodes and topics](/notes/ros2-topics/)

| Contract | What to check |
| --- | --- |
| Time | Use one `/clock` publisher for the simulation. Set `use_sim_time` on consumers such as RViz that should follow it. Keep sensor and transform timestamps in the same time domain. |
| Frames | TF provides transforms between named frames at a given time. Use the sensor message's `header.frame_id` and follow the TF chain to the consumer's fixed frame. Dynamic transforms use `/tf`. Static transforms are normally sent on `/tf_static`. |
| Delivery | Quality of Service (QoS) controls properties such as reliability, durability, and queue depth. A reliable subscription cannot receive from a publisher offering only best effort. Sensor streams commonly favor recent samples. |

## Follow execution, data, and time through the graph

```text
On Playback Tick -- exec -----------------> ROS 2 Publish Clock
Isaac Read Simulation Time -- seconds ---->         | /clock
                                                    v
                                             Jazzy time source

Camera prim --- render product ---> Camera helpers ---> RGB + CameraInfo
   |                                 (render pipeline)         |
   |                                                           v
   +--- TF target ---> Compute Transform Tree ---> Publish TF  consumer
                                                         |     ^
                                                         +-----+
                              resolve image frame at its header stamp
```

The first lane shows why entering Play matters. A time value is data, while an execution edge tells a node when to publish. For a manual clock graph connect the tick to the publisher's execution input, the simulation time to the timestamp input, and the ROS 2 Context to the publisher's context. With a context configured to use the domain from the environment, the value must be set before launching Isaac Sim. Keep one such clock in the domain. A bag playing with its own clock and a live simulator would give consumers competing time authorities. If you reset time on Stop, treat the jump as a run boundary for buffers and logs. A new episode can also use a local time origin while the published clock remains monotonic. [NVIDIA clock tutorial](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_clock.html) · [Tabletop capstone](/notes/capstone-tabletop/)

The camera lane starts with a selected camera prim. A render product binds that camera to an output with a resolution. The RGB helper sets up a runtime postprocessing and publication pipeline for that product. The Camera Info helper publishes calibration and metadata. An authored camera can be visible in the Stage panel with no active product, and a working clock can coexist with a disabled camera pipeline. Test those paths independently. For a new stage, a graph shortcut saves setup time. A manual graph makes the execution and data wiring easier to inspect when diagnosing a custom sensor. Inspect the sample's Action Graph before adding a graph of your own. [NVIDIA camera graph](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_camera.html)

For a custom stage in 6.1.0, put the camera or articulation root in the **Isaac Compute Transform Tree** node's `targetPrims`. The playback tick drives compute. Wire its execution output and its parent, child, translation, and orientation arrays to **ROS 2 Publish Transform Tree**. Give the publisher simulation time and the ROS 2 Context. Check that the camera's published frame has the expected optical axes as well as the expected name. A camera whose frame resolves but projects points in the wrong direction has a geometry problem. Choosing the latest available transform may hide a time gap but changes a moving camera's pose. [NVIDIA TF graph](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_tf.html) · [ROS 2 Jazzy QoS](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Quality-of-Service-Settings.rst)

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

**Checkpoint.** Check for one clock publisher and advancing timestamps while playing. Pause and verify that simulation time stops advancing. Compare the frame in `CameraInfo` and the RGB header with the transform tree. One `/tf` message may contain only part of that tree. In RViz, set `use_sim_time` to true and choose a fixed frame with a path to the sensor. Inspect the chain while playing, using `ros2 run tf2_tools view_frames --ros-args -p use_sim_time:=true` if the `tf2_tools` package is present. A topology check still needs to be followed by a lookup at the image timestamp for a moving sensor. [NVIDIA clock tutorial](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_clock.html)

## Vary capture rate and explain what you measured

The rate tutorial uses two scheduling mechanisms. The clock publishes on playback ticks. The IMU gate in that fixture runs every second playback tick. The camera uses its prim's sensor tick rate, subject to renderer updates. Even when these are all configured coherently, a machine that cannot keep up with rendering can advance less than one simulated second per wall second. ROS delivery can impose another limit. Record the configured settings and the observed clocks so you can distinguish where time was lost. [NVIDIA simulation rate setup](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_publish_rate.html#setting-the-simulation-rate)

Use `ros2 topic echo /camera_1/rgb/camera_info --field header` to collect stamps at the baseline of 15 camera captures per simulated second. Estimate the gap from several consecutive stamps, converting each with `sec * 1_000_000_000 + nanosec` before subtraction. Also record image arrivals with `ros2 topic hz` and estimate real-time factor as the change in `/clock` divided by the elapsed wall time over a steady window. Measure after startup and keep the same probes for the comparison. Echoing full RGB payloads can itself add work.

While stopped, change only `/World/Camera_1`'s `omni:sensor:tickRate` from 15 to 10 and replay. Leave the deprecated frame-skip setting at zero. At the chosen nominal rate of 60 updates per simulated second, these settings permit one capture every four or six updates, respectively. Compare captured stamp gaps with the expected 67 ms and 100 ms gaps. For example, an illustrative run at 10 Hz has camera stamps of 12.000, 12.100 and 12.200 s. If the clock advances by 2 simulated seconds in 4 wall seconds, expect about five image arrivals per wall second before loss. A measurement near 5 Hz would be consistent with that run. If CameraInfo stays near that rate but RGB arrives at 2 Hz, inspect the image path rather than changing the time model. [NVIDIA sensor rate controls](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_publish_rate.html#rtx-sensors)

## Debug one boundary and rerun

Begin at Play and discovery if the topic list is empty. Check the bridge startup log, ROS context domain, and middleware in both shells. When a publisher is discoverable but data does not arrive, inspect offered and requested QoS with `ros2 topic info -v`. To test compatibility with a best-effort camera publisher, use a best-effort probe such as `ros2 topic echo /camera_1/rgb/image_raw --field header --qos-reliability best_effort --once`. If there is still no data, check that the correct render product and helper are enabled. Reliable delivery helps consumers that need each sample, but retransmission and queued work can increase age. A shallow best-effort queue can suit real-time perception that can tolerate gaps.

If images arrive and TF fails, inspect the frame chain and the time window. For example, a header stamped 12.200 s and a dynamic TF buffer covering 12.000 through 12.167 s have a 33 ms future extrapolation gap. A bounded wait for a newer transform is reasonable if both streams share a clock. A TF clock near Unix epoch seconds and an image stamp of 12.200 s indicate different clock domains. Increasing queue depth cannot align those domains. Keep the trace, correct the producer or consumer time setting, and rerun the same sample-time lookup. When frame and time checks pass but image delivery is slow, try one smaller resolution at the same sensor tick rate. Compare the change in real-time factor and RGB arrivals before deciding whether rendering or delivery needs more investigation.

## Exercises and solutions

The image topic is visible and `ros2 topic hz` shows arrivals, but RViz reports that the image's frame is unknown. What do you inspect first?

<details>
<summary>Check your answer</summary>
<p>Read the image's frame ID and trace it to the fixed frame. If that path exists, check whether TF covers the image timestamp and whether RViz follows the same clock.</p>
</details>

The camera publishes at 15 Hz in simulated time. Over six wall seconds the clock advances by three seconds. CameraInfo arrives at about 7.5 Hz and RGB at about 3 Hz. What can you infer, and what would you change first?

<details>
<summary>Check your answer</summary>
<p>The real-time factor is 0.5, which explains about 7.5 arrivals per wall second. The extra RGB shortfall concerns the image pipeline or its measurement. Compare subscriber QoS and header gaps with CameraInfo. Then vary resolution alone and repeat. If the real-time factor also changes, recompute the expected arrival rate for the new run.</p>
</details>

## Common misconceptions

- **Topic discovery proves delivery.** A graph can advertise a publisher whose QoS or execution state prevents your subscriber from receiving samples.
- **The topic rate is the camera's configured rate.** Arrival rate incorporates simulation speed, publication work, transport and subscriber capacity.
- **Setting `use_sim_time` rewrites message headers.** It changes the consumer's clock. Publishers still choose their own header stamps.

## Summary

Prove clock authority, sample delivery, and a transform lookup at the acquisition time before trusting an external observation. Compare stamp intervals with wall-time arrivals under a single deliberate rate change. Those two measurements tell you which part of the graph to inspect next.

Continue to [simulation experiments](/notes/isaac-experiments/) and use these checks when attaching a camera to the capstone arm.
