---
title: Design robotics networks and artifact storage
topic: Infrastructure
order: "102"
description: Diagnose ROS 2 discovery, budget camera traffic, and preserve the files and clocks needed for replay.
prerequisites: Understand ROS 2 publishers, subscribers, and topic types
minutes: 50
---

## Discovery, delivery, and isolation

Your recorder sees the camera topic but the bag has gaps. A teammate copies the bag to a laptop and cannot replay it. These failures need separate evidence. The network must discover and match endpoints, the recorder must sustain the incoming load, and the exported artifact must restore with enough context to decode its contents.

Aim for three observable results. Receive a synthetic message on the intended domain and observe a timeout after changing only the subscriber's domain. Calculate the capture budget before requesting two cameras, then compare actual publisher and receiver counts during a bounded run. Finally restore a sample into a clean directory and check both its bytes and its contents. These checks tell you which failure to take on first.

DDS is the middleware used by most ROS 2 configurations. Its participants discover other participants, then try to match publishers and subscribers by topic, type, and compatible Quality of Service (QoS). `ROS_DOMAIN_ID` groups participants into logical networks. A matching ID is only one requirement. Network reachability, the middleware configuration, and matching endpoint settings also matter.

Use an assigned lab domain and limit discovery to the local machine for replay. With Jazzy's DDS-based default middleware and no static peers, `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` restricts automatic discovery to the local machine. The same knobs do not apply to `rmw_zenoh`. Domain IDs provide no authentication. Keep physical controllers on a separate network segment with firewall rules, and use an approved telemetry gateway or inspected file export to move data. A Docker network or WSL2 NAT is a separate boundary. Windows WSL mirrored networking supports multicast, and firewall rules still apply. [Jazzy discovery settings](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Advanced/Improved-Dynamic-Discovery.rst), [ROS domain IDs](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Domain-ID.rst), [Microsoft WSL networking](https://learn.microsoft.com/en-us/windows/wsl/networking).

![A real robot and recorder share an isolated robot network. A reviewed file export moves to the lab, where local replay feeds an analysis subscriber. No live DDS route joins the networks.](/assets/infra-dds-boundaries.svg)

Read the diagram from left to right. The recorder sits near the producer so high-rate samples stay on the capture segment. Only the reviewed export crosses into the replay lab. A domain change helps prevent accidental discovery on a shared segment. Firewall and network boundaries control which machines can communicate. Keeping replay local also means a missed message can be investigated without access to a robot.

## Lab · Find the first broken boundary

**Design.** Begin with a small string topic so transport load and disk throughput are irrelevant to the test. Use two fresh Bash terminals in the **same** preconfigured Jazzy Linux or WSL2 environment, disconnected from physical robots. Run this preamble in both. Use the default DDS middleware with its default transport configuration.

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
unset ROS_STATIC_PEERS
```

In terminal A, start a harmless synthetic publisher. Stop it with Ctrl+C after the exercise.

```bash
ros2 topic pub --rate 2 /infra_probe std_msgs/msg/String '{data: probe}'
```

**Observe and vary.** In terminal B, compare a matching domain with a deliberately different one. The prefix changes the domain for the second invocation only. The outcomes below are predictions for this setup.

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

**Debug and iterate.** Restore domain 42 and use `ros2 topic info --no-daemon -v /infra_probe` to query the local graph directly. Run it from a third shell with the same preamble while the subscriber is still waiting to inspect both endpoints. Check the producer count, type, and offered versus requested policies before measuring delivery. A daemon left running with different settings can make a graph query misrepresent the shell you are testing. [Jazzy topic info source](https://github.com/ros2/ros2cli/blob/jazzy/ros2topic/ros2topic/verb/info.py).

Once domain 42 passes again, isolate a QoS failure. First run the echo with `--qos-reliability reliable` on the original publisher. Then stop and replace the publisher with the same command plus `--qos-reliability best_effort`. Keep the subscriber explicitly reliable. Expect an advertised publisher but no matching reliable delivery. Switch only the subscriber to `--qos-reliability best_effort` and expect the message again. In live perception, recent data may matter more than recovering every packet. For offline capture, retransmission can improve completeness at the cost of extra traffic, queues, and latency. Check both recorder and producer counters before deciding. [Jazzy QoS compatibility](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Quality-of-Service-Settings.rst), [Jazzy echo options](https://github.com/ros2/ros2cli/blob/jazzy/ros2topic/ros2topic/verb/echo.py).

For a cross-host transfer exercise on a permitted lab segment, verify the interface and reachability first. Multicast discovery may fail across NAT or a container bridge even when a unicast connection works. Static peers provide explicit discovery targets and require reachable addresses and compatible settings on the participants. Test the same small topic across the boundary before sending sensor traffic. If it passes while camera delivery fails, the small message has already eliminated a general discovery failure for that configuration.

## Work the bandwidth and storage budget

For tightly packed RGB8, 1280 × 720 × 3 gives 2,764,800 bytes per frame. Multiply by 30 frames/s to get 82,944,000 bytes/s, about **83 MB/s or 664 Mb/s** using decimal units. Two such cameras require **166 MB/s or 1.33 Gb/s** of pixel payload. A 1 Gb/s link can carry at most 125 MB/s before overhead. A raw two-camera stream exceeds even that ideal limit. If an image has row padding, use bytes per row times height. Include other topics, serialization, packet overhead, and burst headroom when designing the full path.

At 30 minutes, the two raw streams contribute `165,888,000 × 1,800 = 298,598,400,000` bytes, about **299 GB**. Adding a 25% planning reserve gives about **373 GB** free for that capture alone. The written bag size depends on format and compression, and both restore and upload staging can require more space. Keeping five captures at the same raw rate takes about 1.49 TB before reserves or replication. Estimate separate budgets for the live link, local write path, and retained copies.

Start with one camera for a bounded interval. Record the producer count, receiver count, recorded count, and elapsed time from the same capture window. In separate terminals, `ros2 topic hz /camera/image_raw` and `ros2 topic bw /camera/image_raw` estimate what their subscriptions receive. They can add load and do not measure wire utilization. Compare with host interface counters and `ros2 bag info <bag-directory>` after recording. Use source stamps or sequence identifiers when available because equal totals can conceal duplicates. Add the second stream as the only changed input. If received counts first drop across the link, inspect link utilization and subscriber scheduling. If receive counts hold but bag counts fall, inspect recorder queues and sustained disk writes. [Jazzy bandwidth implementation](https://github.com/ros2/ros2cli/blob/jazzy/ros2topic/ros2topic/verb/bw.py), [rosbag2 Jazzy](https://github.com/ros2/rosbag2/blob/jazzy/README.md).

Recording at the source puts disk demand near the cameras and avoids sending raw frames across the constrained link. Compression reduces bytes at the expense of CPU or GPU work, decode latency, and possible loss of image detail. Reducing frame rate saves bytes immediately but can hide short contact events. Repeat the same capture test after changing one of these choices.

## Carry clocks and test an artifact restore

On multi-host capture, use a common wall-clock reference via NTP or PTP as required by the timing budget, and log measured clock offsets. Preserve device capture timestamps alongside receive times. If camera A stamps an event 4 ms ahead of the reference and camera B 3 ms behind, a 7 ms difference can appear in the recorded stamps even when the event was simultaneous. Preserve the original stamps and document any offset correction.

For simulation and replay, select one `/clock` source and set `use_sim_time` on consumers that should follow it. Pick the recorded clock or the player's generated clock based on the bag and its header stamps. Jazzy's `ros2 bag play <bag-directory> --clock` excludes recorded `/clock` and generates a replay clock. Stop any simulator clock publisher before playing. Compare header stamps against the selected clock and TF before interpreting replay. Maintain the capstone's observation-before-action ordering. The Isaac Franka capture and LeRobot PushT evaluation each have their own artifact contract and require an explicit adapter to connect. [Jazzy rosbag2 playback options](https://github.com/ros2/rosbag2/blob/jazzy/ros2bag/ros2bag/verb/play.py).

```text
 Capture host                Replay host
 frame + capture stamp       verified copy + original stamp
    |                             |
    v                             v
 recorder -> bag + metadata -> player -> analysis subscriber
                                          ^
                              one replay clock for ROS time
```

Follow the source timestamp through the file path. The clock path at the bottom lets the receiving node interpret timestamps during replay. A shared replay clock preserves any misalignment already present in the recording.

Stage high-rate writes on local SSD, then upload completed artifacts to versioned object storage. Keep small manifests in Git with checksums, storage URIs, licenses, and retention. Preserve bag metadata, chunks, and message definitions together. Preserve a USD stage with its referenced layers and textures, datasets with video shards and episode indexes, and policy weights with their config and normalization statistics. Restore a small sample onto a clean machine and verify the hashes, one decoded frame, and the bag's topic metadata. [rosbag2 Jazzy](https://github.com/ros2/rosbag2/blob/jazzy/README.md), [OpenUSD asset resolution](https://openusd.org/release/api/ar_page_front.html), [LeRobotDataset v3 in LeRobot v0.4.3](https://huggingface.co/docs/lerobot/v0.4.3/en/lerobot-dataset-v3).

**Restore drill.** In a Bash directory containing the capstone's [validator](/assets/labs/check_trace.py) and [trace fixture](/assets/labs/tabletop-trace.csv), create a manifest and simulate downloading the files into a new directory. This needs GNU coreutils and Python 3. Keep the original checksums from the upload or a trusted run manifest.

```bash
sha256sum check_trace.py tabletop-trace.csv > SHA256SUMS
restore=$(mktemp -d)
cp check_trace.py tabletop-trace.csv SHA256SUMS "$restore/"
(cd "$restore" && sha256sum -c SHA256SUMS &&
  python3 check_trace.py tabletop-trace.csv)
```

Expect two checksum confirmations and `OK: 6 rows across 2 episodes`. Append one byte to the **restored copy** with `printf 'x' >> "$restore/tabletop-trace.csv"`. Repeat the subshell and expect the checksum to fail before Python runs. Copy the original trace back and repeat to recover. This drill separates transfer integrity from format usability. For a real bag, verify its pinned object version and manifest, run `ros2 bag info`, and decode one message on the replay host. A readable topic inventory alone leaves camera decode and replay timing unchecked.

## Exercises

<details>
<summary>Self-check · Both cameras discover successfully, but one recorder drops frames. Would changing the domain help?</summary>
<p>Changing domains changes discovery groups. Measure the total camera load, recorder throughput, and drops. If two raw streams saturate the link, record near the source, reduce rate or resolution, or use compression and measure again.</p>
</details>

<details>
<summary>Transfer · Can two 720p RGB streams at 15 Hz share the link and fit in 150 GB for 30 minutes?</summary>
<p>Halving the rates gives about 664 Mb/s in total, below the theoretical 1 Gb/s capacity. Measure both streams and other traffic to confirm headroom. Pixel data alone adds up to about 149.3 GB. With a 25% reserve, budget about 187 GB before restore space. Use a larger volume, shorten the run, or measure an acceptable compression mode. Check whether 15 Hz still captures the events you need.</p>
</details>

## Common misconceptions

- **“A listed topic proves the subscriber can receive it.”** Check type and offered versus requested QoS, then observe a sample.
- **“The bandwidth probe reports link utilization.”** It reports the probe subscription's rate. Compare with interface counters and producer counts.
- **“The object exists, so the backup works.”** Restore it and verify the bytes, dependencies, and decoded contents.

## Summary

Confirm discovery with a small message, then verify endpoint matching and size the link and disk separately. Measure where counts diverge before changing the network or recorder. Preserve source timestamps and artifact dependencies so replay can demonstrate that the recording is still usable.

Apply the replay boundary and restore check before moving to simulated pick-and-place in the [tabletop capstone](/notes/capstone-tabletop/).
