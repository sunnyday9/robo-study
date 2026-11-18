---
title: Design robotics networks and artifact storage
topic: Infrastructure
order: "42"
description: Diagnose ROS 2 discovery, budget camera traffic, and preserve the files and clocks needed for replay.
prerequisites: Understand ROS 2 publishers, subscribers, and topic types
minutes: 35
---

## Discovery, delivery, and isolation

DDS is the middleware used by most ROS 2 configurations. Its participants discover other participants, then try to match publishers and subscribers by topic, type, and compatible Quality of Service (QoS). `ROS_DOMAIN_ID` groups participants into logical networks. A matching ID is only one requirement. Network reachability, the middleware configuration, and matching endpoint settings also matter.

Use an assigned lab domain and limit discovery to the local machine for replay. With Jazzy's DDS-based default middleware and no static peers, `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` restricts automatic discovery to the local machine. The same knobs do not apply to `rmw_zenoh`. Domain IDs provide no authentication. Keep physical controllers on a separate network segment with firewall rules, and use an approved telemetry gateway or inspected file export to move data. A Docker network or WSL2 NAT is a separate boundary. Windows WSL mirrored networking supports multicast, and firewall rules still apply. [Jazzy discovery settings](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Advanced/Improved-Dynamic-Discovery.rst), [ROS domain IDs](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Domain-ID.rst), [Microsoft WSL networking](https://learn.microsoft.com/en-us/windows/wsl/networking).

![A real robot and recorder share an isolated robot network. A reviewed file export moves to the lab, where local replay feeds an analysis subscriber. No live DDS route joins the networks.](/assets/infra-dds-boundaries.svg)

## Lab · Find the first broken boundary

Use two fresh Bash terminals in the **same** preconfigured Jazzy Linux or WSL2 environment, disconnected from physical robots. Run this preamble in both. Use the default DDS middleware with its default transport configuration.

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
unset ROS_STATIC_PEERS
```

In terminal A, start a harmless synthetic publisher. Stop it with Ctrl+C after the exercise.

```bash
ros2 topic pub --rate 2 /infra_probe std_msgs/msg/String '{data: probe}'
```

In terminal B, compare a matching domain with a deliberately different one. The prefix changes the domain for the second invocation only.

```bash
ros2 topic echo /infra_probe std_msgs/msg/String --once --timeout 8
ROS_DOMAIN_ID=43 ros2 topic echo /infra_probe std_msgs/msg/String --once --timeout 8
```

| Observation | Next check |
| --- | --- |
| Domain 42 prints `data: probe`, domain 43 times out | Expected. Restore matching domains for communication and keep the network boundary for isolation. |
| Both time out on the same host | Check that the publisher is still running, then compare domain, middleware, discovery scope, and topic/type in both shells. |
| Local test succeeds, cross-host discovery fails | Check container or WSL network mode, interfaces, multicast, and firewall policy. Use the documented peer configuration on an authorized lab segment if multicast is unavailable. |
| Endpoints are visible but delivery stalls | Inspect `ros2 topic info -v /infra_probe` for offered and requested QoS. A reliable subscriber cannot match a best-effort publisher. Check publish rate and transport load after QoS. |

## Budget bytes and carry clocks

One raw RGB camera at 1280 × 720 × 3 bytes × 30 Hz produces about 83 MB/s, or 664 Mb/s before protocol overhead. Two exceed a 1 Gb/s link. Budget for peaks and additional topics. Record near the source or compress intentionally, then measure rate, latency, and drops with all streams active.

On multi-host capture, use a common wall-clock reference via NTP or PTP as required by the timing budget, and log measured clock offsets. Preserve device capture timestamps alongside receive times. For simulation and replay, select one `/clock` source and set `use_sim_time` on consumers that should follow it. A replay clock cannot repair misaligned acquisition timestamps. [Jazzy rosbag2 playback options](https://github.com/ros2/rosbag2/blob/jazzy/ros2bag/ros2bag/verb/play.py).

Stage high-rate writes on local SSD, then upload completed artifacts to versioned object storage. Keep small manifests in Git with checksums, storage URIs, licenses, and retention. Preserve bag metadata, chunks, and message definitions together. Preserve a USD stage with its referenced layers and textures, datasets with video shards and episode indexes, and policy weights with their config and normalization statistics. Restore a small sample onto a clean machine and verify the hashes, one decoded frame, and the bag's topic metadata. [rosbag2 Jazzy](https://github.com/ros2/rosbag2/blob/jazzy/README.md), [OpenUSD asset resolution](https://openusd.org/release/api/ar_page_front.html), [LeRobotDataset v3 in LeRobot v0.4.3](https://huggingface.co/docs/lerobot/v0.4.3/en/lerobot-dataset-v3).

<details>
<summary>Self-check · Both cameras discover successfully, but one recorder drops frames. Would changing the domain help?</summary>
<p>Changing domains changes discovery groups. Measure the total camera load, recorder throughput, and drops. If two raw streams saturate the link, record near the source, reduce rate or resolution, or use compression and measure again.</p>
</details>

Apply the replay boundary and restore check before moving to simulated pick-and-place in the [tabletop capstone](/notes/capstone-tabletop/).
