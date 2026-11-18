---
title: "回放 ROS 2 数据并测试通信图"
topic: "ROS 2"
order: "064"
description: "捕获重放装置、引脚启动参数并隔离发现、时间和应用程序故障。"
prerequisites: "Jazzy 心跳实验室、QoS 和 ROS 时间。"
minutes: 45
---

## 重现故障而不重新运行仿真器

仿真器重启后，感知节点有时会停止。重新运行场景可以更改输入、调度和时钟。冻结一个短输入窗口，以便你可以一次测试一个变量。首先使用积极的消息计数进行心跳记录。将其回放到一个新的进程，并在实际经过的时间截止日期之前检查五个递增的序列值和前进的消费者时钟。然后仅更改一个播放标志并预测哪项检查将失败。该练习在 Ubuntu 24.04 上使用 ROS 2 Jazzy 构建软件装置。

## 知道哪个时间戳可以回答你的问题

rosbag2 记录存储序列化消息、主题元数据和计时信息。对于本实验中的普通回放，与包条目关联的时间戳安排其回放。消息的 `header.stamp`（如果存在）具有发布者定义的任何含义。使用原始采集标记将传感器读数加入 TF。使用行李时间线来练习到达顺序和节奏。心跳没有报头，这使得它对于将传输和时钟检查与采集时间几何结构分离非常有用。

```text
Illustrative capture from one simulation clock (seconds)

                                 Observation A        Observation B
Message header: acquired at          12.000               12.100
Bag entry: recorder clock reads      12.040               12.110
Playback: wall offset at 1x           0.000                0.070
Playback: wall offset at 2x           0.000                0.035
                                      |                    |
TF lookup after either replay        12.000               12.100
```

偏移量是相对于第一个条目的并且是理想化的。采集间隔为 100 ms。记录器在其时间轴上看到相隔 70 毫秒的条目，因此 2× 播放器的目标是 35 毫秒的墙时间间隙。播放速率都不会改变有效负载中的采集标记。由于订阅者、中间件和执行程序再次运行，到达时间仍可能与计划有所不同。这就是为什么包可以重现记录的输入，同时产生不同的下游回调顺序或时间。

在模拟运行中，`ros2 bag record --use-sim-time` 使用记录仪最新收到的 `/clock` 作为数据包接收时间戳。它在订阅录制的流之前等待时钟启动。如果你希望其原始消息可供以后检查，请明确选择 `/clock`。使用 `ros2 bag play ... --clock 10`，播放器以配置的频率从其播放时间线发布生成的时钟，并排除包自己的 `/clock` 主题的回放。让其他时钟发布者远离此图表，并在应该关注玩家的消费者上设置 `use_sim_time`。在系统时间时间轴上捕获的包可以使用生成的时钟重放，但无法修复在不同时钟下记录的仿真时间标头。 [Jazzy rosbag2 录音指南](https://github.com/ros2/rosbag2/tree/jazzy#simulation-time) · [Jazzy 录音机源](https://raw.githubusercontent.com/ros2/rosbag2/jazzy/rosbag2_transport/src/rosbag2_transport/recorder.cpp) · [Jazzy 播放标志](https://raw.githubusercontent.com/ros2/rosbag2/jazzy/ros2bag/ros2bag/verb/play.py)

## 实验室 — 覆盖参数、记录和重放

在每个终端中输入 `~/robo_ws/lab-env.bash`。阻止早期的实验室出版商。如果 `ros2 bag` 不可用，请安装 `ros-jazzy-rosbag2`。将此可运行启动文件保存为 `~/robo_ws/heartbeat.launch.py`。将句点固定在启动文件中将夹具与可检查的启动配置联系起来。在一个进程上进行试验时，直接覆盖 `ros2 run` 会更快。当多个节点必须以协调的参数启动时，启动非常有用。 [工作空间设置](/zh/notes/ros2-workspaces/)

```python
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='tabletop_tools',
            executable='heartbeat',
            parameters=[{'period_s': 0.25, 'use_sim_time': False}],
        ),
    ])
```

Launch 声明进程及其启动值。节点在创建定时器时声明参数类型并读取 `period_s`，因此本示例将周期设置为只读。在终端 A 中启动 `ros2 launch ~/robo_ws/heartbeat.launch.py`。检查实时参数并在 B 中记录主题。

```bash
ros2 param get /tabletop_heartbeat period_s
cd ~/robo_ws
ros2 bag record -o heartbeat_bag --topics /tabletop/heartbeat
```

预期为 0.25 秒的两倍。在记录器报告订阅后至少记录八秒，然后使用 Ctrl+C 停止记录，以便完成包。停止 A 中的实时启动。在每个新录制中使用新的输出目录名称。对于八整秒的稳定输入，4 Hz 意味着大约 32 个样本。将其视为估计值，因为你的停止时间和接收率会影响计数。

在 B 中，运行 `ros2 bag info heartbeat_bag`。检查正消息计数以及预期的主题和类型。在 A 中启动数据回显，如果你有第三个终端，则在此处启动时钟回显。然后在B中开始播放。

```bash
# A: data observer
ros2 topic echo /tabletop/heartbeat std_msgs/msg/String --once

# C: optional clock observer
ros2 topic echo /clock rosgraph_msgs/msg/Clock --qos-reliability best_effort --once

# B: run from ~/robo_ws
ros2 bag play heartbeat_bag --clock 10
```

期望记录 `beat N` 和重放时钟样本。使用你的启动配置记录实际持续时间、消息计数和观察到的一个有效负载。如果计数为零，请首先诊断记录器的图表、主题和 QoS。如果包包含输入但回显失败，请检查玩家的端点。如果回声有效，但基于时间的逻辑停滞，请检查消费者是否遵循一个前进的时钟。看到一条 `/clock` 消息就确定了向 echo 进程的传送。消费者体内时钟的提前需要再次检查。 [Jazzy启动指南](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Creating-Launch-Files.html)

## 区分发现失败和重放失败

当实时心跳启动在 A 中运行时，在 B 中运行这些探测器。如果回放处于活动状态，请首先停止播放器。

| B的设置 | /tabletop_heartbeat 的预期可见性 |
| --- | --- |
| `ros2 node list --no-daemon --spin-time 2` | 通过匹配的本地设置可见 |
| `ROS_DOMAIN_ID=73 ros2 node list --no-daemon --spin-time 2` | 如果 A 使用域 72，则不存在 |
| `ROS_AUTOMATIC_DISCOVERY_RANGE=OFF ros2 node list --no-daemon --spin-time 2` | 没有此快速 DDS 设置 |

这些单命令覆盖使 B 的 shell 设置保持不变。如果实验室使用 73，请使用不同的不匹配值。如果直接列表有效但普通列表不同，请在预期环境中使用 `ros2 daemon stop` 和 `ros2 daemon start` 重新启动 CLI 守护程序。对于跨主机 DDS 设置，比较域、中间件、发现范围、静态对等点和多播可达性。由于没有静态对等点，实验室的 `LOCALHOST` 系列将发现限制在同一台机器上。 Zenoh 使用自己的发现配置。在重新启动重放测试之前再次停止实时启动。 [Jazzy 发现设置](https://docs.ros.org/en/jazzy/Tutorials/Advanced/Improved-Dynamic-Discovery.html)

## 一次开发一个测试边界

从数据不变量开始。使用 capstone 的[跟踪验证器](/assets/labs/check_trace.py) 和[教学 CSV](/assets/labs/tabletop-trace.csv)。将它们保存在一起并从该目录运行这些命令。第二个命令创建一个单独的夹具，仅更改第一行的指令时间戳。

```bash
python3 check_trace.py tabletop-trace.csv
sed '2s/,1000000,open/,11000000,open/' tabletop-trace.csv > tabletop-trace-late.csv
python3 check_trace.py tabletop-trace-late.csv
```

教学设备应报告 `OK: 6 rows across 2 episodes`。突变的装置应以非零值退出并出现倾斜误差：其第一个命令遵循零标记观察 11 毫秒，默认预算为 10 毫秒。这可以快速测试数据规则，无需 ROS 进程。顶峰需要在整个出口管道采取行动之前进行观察。如果导出器配对了错误的样本，则具有允许偏差的行仍然可能包含错误的操作，因此还要保留已知值的固定装置。

将手动回波变成有界积分探头。将以下内容另存为 `~/robo_ws/check_heartbeat.py`。它使用已安装的 Jazzy Python 库。它分别监视序列和时间，以便超时可以命名丢失的证据。此交付烟雾测试允许序列中存在间隙。重复或减少都是失败，因为该特定赛程来自一次不间断的发布者运行。

```python
import time

import rclpy
from std_msgs.msg import String


def main():
    rclpy.init()
    node = rclpy.create_node('check_heartbeat')
    count = 0
    previous = -1
    first_clock_ns = None
    clock_advanced = False

    def on_beat(message):
        nonlocal count, previous
        prefix, _, suffix = message.data.partition(' ')
        if prefix != 'beat' or not suffix.isascii() or not suffix.isdecimal():
            raise ValueError(f'unexpected heartbeat: {message.data!r}')
        number = int(suffix)
        if number <= previous:
            raise ValueError(f'heartbeat did not increase: {previous} -> {number}')
        previous = number
        count += 1

    try:
        if not node.get_parameter('use_sim_time').value:
            raise SystemExit('FAIL: start the probe with use_sim_time:=true')
        node.create_subscription(String, '/tabletop/heartbeat', on_beat, 10)
        deadline = time.monotonic() + 15.0
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            now_ns = node.get_clock().now().nanoseconds
            if first_clock_ns is None and now_ns > 0:
                first_clock_ns = now_ns
            elif first_clock_ns is not None and now_ns > first_clock_ns:
                clock_advanced = True
            if count >= 5 and clock_advanced:
                print('OK: received increasing heartbeats and observed replay time advance')
                return
        raise SystemExit(f'FAIL: received={count} (need >=5), replay_clock_advanced={clock_advanced}')
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
```

在几秒钟内启动 A 中的探测器和 B 中的播放器。用新的探测器开始每次尝试，并确保前一个玩家退出。延迟使端点可以在第一个包消息之前发现彼此。

```bash
# A
/usr/bin/python3 ~/robo_ws/check_heartbeat.py --ros-args -p use_sim_time:=true

# B (from ~/robo_ws)
ros2 bag play heartbeat_bag --delay 2 --clock 10
```

一旦通过，保持文件、延迟和订阅者设置固定，并在一次运行中省略 B 中的 `--clock 10`。该包仅包含心跳消息。预计探测器会对节拍进行计数，但会失败并显示 `replay_clock_advanced=False`。如果两项检查均失败，请在将故障归因于时钟之前调查交付情况。如果两者都通过，请在播放期间检查 `ros2 topic info -v /clock` 是否有其他权限。恢复`--clock 10`并再次确认成功。即使 ROS 时间停止，单调截止时间也可以观察到丢失时钟的情况。

要自动化进程，请将进程启动和关闭移至其自己的 ROS 域上的 `launch_testing` 测试中。启动探测器和播放器，断言在实际经过的时间预算内成功探测器退出，并检查干净的进程关闭。将无时钟情况作为阴性对照并断言时钟诊断。注册你的包的测试，并在 `colcon test` 之后使用 `colcon test-result --verbose` 检查故障。终端探针在 Jazzy 上运行时已经测试了实际的消息传递和时间。测试工具将删除手动启动顺序并收集重复运行的证据。 [Jazzy 集成测试](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Testing/Integration.html)

## 将夹具扩展到标记的观测结果

与合成联合出版商和国家出版商在 [帧和时间](/zh/notes/ros2-frames-and-time/) +90 度处重复录制。使用 `ros2 bag record -o tabletop_tf_bag --topics /joint_states /tf /tf_static` 进行记录。验证所有三个流都有消息。在使用 `--clock 10` 回放 `tabletop_tf_bag` 之前停止实时发布者，并在玩家之前启动新的 `tf2_echo` 观察者。将基础到工具的转换与实时检查点进行比较。如果固定转换丢失，请检查 `/tf_static` 的包计数以及记录器和播放器 QoS。为了在加入较晚后接收保留的转换，发布者和订阅者都需要瞬时本地持久性。

[桌面顶点](/zh/notes/capstone-tabletop/) 添加了一个带标记的观察发布器和一个精确时间 TF 检查器。这将测试扩展到采集时几何的交付之外。将 Python 3.12 中的 Isaac Sim 6.1.0 Franka 回放和 LeRobot 0.4.3 PushT 实验室保留为单独的实验，除非显式适配器提供数据集契约。保留先观察后行动的配对，并为每个图表使用一个仿真时钟权威。

## 练习

1. 解释利率变化。两条消息的采集标记相隔 20 毫秒，包输入时间相隔 60 毫秒。预测半速时的标称壁间隙、订阅者处的标头间隙以及将使用哪个间隙来将观测值与 TF 进行匹配。

<details>
<summary>解决方案</summary>
<p>半速将 60 毫秒的播放间隔延长至大约 120 毫秒的挂机时间。有效负载的标头间隙保持 20 毫秒。在每个原始采集标记处查找 TF。使用秒表计时来单独调查重放性能。</p>
</details>

2. 调试非空包。探测器收到十个递增的节拍，然后报告 `replay_clock_advanced=False`。更改心跳主题上的 QoS 没有任何效果。说出接下来的两个探针并解释它们告诉你什么。

<details>
<summary>解决方案</summary>
<p>检查<code>/时钟</code>在玩游戏时检查预期的发布者是否存在并观察至少两个递增的时钟值。然后检查消费者的<code>使用仿真时间</code>设置及其时钟读数。这将丢失或暂停的播放时钟与从不遵循它的消费者区分开来。心跳计数器已经在其自己的订阅上建立了交付。</p>
</details>

## 常见的误解

- The bag timestamp replaces the header stamp.播放器安排序列化消息并保留其有效负载。
- A nonempty bag guarantees a complete fixture.验证所需的流、计数和 QoS，包括保留的静态转换。
- Playback resets every consumer.查找或循环时，处理时钟跳跃并清除时间索引的应用程序状态，以便旧数据不会在重置时泄漏。

## 总结

记录一个小装置并记录哪个时钟定义其时间线。从数据不变量开始，检查有界订阅者的实际回放，然后删除所需的输入以证明检查可能会失败。仅在交货和时间独立后添加冲压几何形状。
