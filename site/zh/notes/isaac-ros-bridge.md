---
title: "通过 ROS 2 读取仿真传感器数据"
topic: "Isaac Sim"
order: "083"
description: "启动 ROS 2 桥并使用时钟、帧和交付检查来解释丢失或缓慢的传感器数据。"
prerequisites: "Ubuntu 24.04 上的 Isaac Sim 6.1.0 和基本 ROS 2 主题"
minutes: 50
---

## 使相机示例可以在仿真器之外使用

你可以在 Isaac Sim 中看到相机视图，但在 ROS 程序中仍然有无法使用的观测结果。程序可能不会收到任何信息，收到时间戳不兼容的帧，或者收到无法与机器人位姿关联的良好像素。在将策略连接到仿真器之前，请证明外部 Jazzy 进程可以看到一个前进的仿真时钟、接收经过标记的相机样本，并且可以在样本时间解释帧。然后解释为什么测量的到达节奏与配置的捕获节奏一致或不同。

该桥将选定的模拟状态和传感器产品转换为类型化的 ROS 消息。它还可以翻译传入的命令，该实验室未连接这些命令。将实验室保留在本地仅用于仿真的域上可以使桥的发布路径更易于调试，并在通过 ROS 添加任何反馈之前为你提供已知的观察流。 [ROS 2 节点和主题](/zh/notes/ros2-topics/)

| 合同 | 要检查什么 |
| --- | --- |
| 时间 | 使用一台 `/clock` 发布器进行模拟。在应遵循的消费者（例如 RViz）上设置 `use_sim_time`。将传感器和转换时间戳保持在同一时域中。 |
| 镜框 | TF 提供给定时间命名帧之间的转换。使用传感器消息的`header.frame_id`并沿着TF链到达消费者的固定框架。动态转换使用 `/tf`。静态转换通常在 `/tf_static` 上发送。 |
| 发货 | 服务质量 (QoS) 控制可靠性、耐用性和队列深度等属性。可靠的订阅无法从仅提供尽力而为的发布者处获得。传感器流通常倾向于最近的样本。 |

## 通过图表跟踪执行、数据和时间

<figure class="lesson-figure">
  <a href="/assets/figures/isaac-bridge.svg"><img src="/assets/figures/isaac-bridge.svg" width="640" height="375" loading="lazy" decoding="async" alt="时钟、标记图像和校准以及相机转换是 ROS 消费者的单独输入。"></a>
  <figcaption>独立检查分支机构。可见图像证明了相机的传输，而不是消费者可以在图像标记处找到变换。</figcaption>
</figure>

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

第一条泳道说明了为什么进入比赛很重要。时间值是数据，而执行边缘告诉节点何时发布。对于手动时钟图，将控制步连接到发布者的执行输入，将仿真时间连接到时间戳输入，并将 ROS 2 上下文连接到发布者的上下文。如果上下文配置为使用环境中的域，则必须在启动 Isaac Sim 之前设置该值。在域中保留一个这样的时钟。一个带有自己的时钟和实时仿真器的包将为消费者提供竞争的时间权威。如果你在停止时重置时间，请将跳转视为缓冲区和日志的运行边界。新回合还可以使用本地时间原点，而发布的时钟保持单调。 [NVIDIA时钟教程](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_clock.html) · [桌面顶点](/zh/notes/capstone-tabletop/)

相机通道从选定的相机原点开始。渲染产品将该相机绑定到具有分辨率的输出。 RGB 帮助程序为该产品设置运行时后处理和发布管道。相机信息助手发布校准和元数据。创作的相机可以在没有活动产品的舞台面板中可见，并且工作时钟可以与禁用的相机管道共存。独立测试这些路径。对于新阶段，图形快捷方式可以节省设置时间。诊断自定义传感器时，手动图表使执行和数据接线更易于检查。在添加你自己的图表之前检查示例的操作图表。 [NVIDIA相机图](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_camera.html)

对于 6.1.0 中的自定义阶段，将相机或关节根放入 Isaac 计算变换树节点的 `targetPrims` 中。播放滴答声驱动计算。将其执行输出及其父级、子级、平移和方向数组连接到 ROS 2 发布转换树。为发布者提供仿真时间和 ROS 2 上下文。检查相机发布的框架是否具有预期的光轴以及预期的名称。相机的框架可以解析但将点投影到错误的方向，则存在几何问题。选择最新的可用变换可能会隐藏时间间隙，但会改变移动相机的位姿。 [NVIDIA TF 图](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_tf.html) · [ROS 2 Jazzy QoS](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Quality-of-Service-Settings.rst)

## 实验室·检查 NVIDIA 的多传感器示例

1. 在同一 Ubuntu 24.04 主机上，使用“默认 ROS 接口”（Default ROS Interfaces） 路径安装 ROS 2 Jazzy。使用快速 DDS。选择一个未使用的仅用于仿真的域（下面的 37）并使主机远离物理机器人网络。在 Isaac Sim 安装目录中的新 Bash 终端中运行以下命令。在窗口 → 扩展中，确认 `isaacsim.ros2.bridge` 已启用。 [NVIDIA 6.1.0桥设置](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_ros.html)

   ```bash
   source /opt/ros/jazzy/setup.bash
   export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
   export ROS_DOMAIN_ID=37
   export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
   unset ROS_STATIC_PEERS
   ./isaac-sim.sh
   ```

2. 在 Isaac Sim Content Browser（内容浏览器）中，打开 Isaac Sim → 示例 → ROS2 → 场景 → `turtlebot_tutorial_multi_sensor_publish_rates.usd`。该模型是实验室的传感器固定装置。在按“播放”之前，请使用 `target_hz = 60` 在脚本编辑器中运行官方教程的“设置模拟速率”片段。它将物理速率和播放速率设置在一起。然后按播放。 [NVIDIA 示例场景和速率设置](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_publish_rate.html#setting-the-simulation-rate)
3. 在第二个 Bash 终端中，检查已发布的消息。这些是可运行的命令。让 `hz` 收集多个样本，然后使用 Ctrl+C 停止它。

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

检查站。检查单时钟发布者并在玩游戏时提前时间戳。暂停并验证仿真时间是否停止前进。将 `CameraInfo` 中的帧和 RGB 标头与变换树进行比较。一条 `/tf` 消息可能仅包含该树的一部分。在 RViz 中，将 `use_sim_time` 设置为 true 并选择具有到传感器路径的固定框架。如果存在 `tf2_tools` 包，请在播放时使用 `ros2 run tf2_tools view_frames --ros-args -p use_sim_time:=true` 检查链条。拓扑检查之后仍然需要查找移动传感器的图像时间戳。 [NVIDIA时钟教程](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_clock.html)

## 改变捕获率并解释你测量的内容

速率教程使用两种调度机制。时钟在播放滴答声上发布。该装置中的 IMU 门每隔一个播放周期运行一次。相机使用其 prim 的传感器滴答率，受渲染器更新影响。即使这些都配置得连贯，一台无法跟上渲染速度的机器每墙每秒的前进速度还不到一个模拟秒。 ROS 传递可能会施加另一个限制。记录配置的设置和观察到的时钟，以便你可以区分时间丢失的位置。 [NVIDIA模拟速率设置](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_publish_rate.html#setting-the-simulation-rate)

使用 `ros2 topic echo /camera_1/rgb/camera_info --field header` 在模拟每秒 15 次相机捕获的基线处收集标记。估计几个连续时间戳的差距，在减法之前用 `sec * 1_000_000_000 + nanosec` 转换每个时间戳。还可以使用 `ros2 topic hz` 记录图像到达情况，并估计实时因子，即 `/clock` 的变化除以稳定窗口上经过的墙时间。启动后进行测量，并保留相同的探头进行比较。回显完整的 RGB 有效负载本身会增加工作量。

停止时，仅将 `/World/Camera_1` 的 `omni:sensor:tickRate` 从 15 更改为 10 并回放。将已弃用的跳帧设置保留为零。在所选的每秒模拟每秒 60 次更新的标称速率下，这些设置允许分别每四次或六次更新捕获一次。将捕获的标记间隙与预期的 67 毫秒和 100 毫秒间隙进行比较。例如，以 10 Hz 运行时的说明性运行具有 12.000、12.100 和 12.200 秒的相机时间戳。如果时钟在 4 墙秒内前进 2 模拟秒，则预计每墙秒大约有 5 个图像到达，然后才会丢失。接近 5 Hz 的测量结果与该运行结果一致。如果 CameraInfo 保持在该速率附近，但 RGB 达到 2 Hz，请检查图像路径而不是更改时间模型。 [NVIDIA 传感器速率控制](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/ros2_tutorials/tutorial_series/tutorial_ros2_publish_rate.html#rtx-sensors)

## 调试一个边界并重新运行

如果主题列表为空，则从播放和发现开始。检查两个 shell 中的桥启动日志、ROS 上下文域和中间件。当发布者可发现但数据未到达时，请使用 `ros2 topic info -v` 检查提供和请求的 QoS。要测试与尽力而为相机发布商的兼容性，请使用尽力而为探针，例如 `ros2 topic echo /camera_1/rgb/image_raw --field header --qos-reliability best_effort --once`。如果仍然没有数据，请检查是否启用了正确的渲染产品和助手。可靠的交付可以帮助需要每个样品的消费者，但重新传输和排队工作可能会增加寿命。浅尽力而为队列可以适应可以容忍间隙的实时感知。

如果图像到达但 TF 失败，请检查帧链和时间窗口。例如，标记为 12.200 秒的标头和覆盖 12.000 到 12.167 秒的动态 TF 缓冲区具有 33 毫秒的未来外推间隙。如果两个流共享时钟，则对更新的转换的有界等待是合理的。接近 Unix 纪元秒的 TF 时钟和 12.200 秒的图像标记表示不同的时钟域。增加队列深度无法对齐这些域。保留跟踪，更正生产者或消费者时间设置，然后重新运行相同的采样时间查找。当帧和时间检查通过但图像传输缓慢时，请在相同的传感器滴答速率下尝试使用较小的分辨率。在决定渲染或交付是否需要更多调查之前，比较实时因素和 RGB 到达的变化。

## 练习题及解答

图像主题可见，并且 `ros2 topic hz` 显示到达，但 RViz 报告图像的帧未知。首先检查什么？

<details>
<summary>检查你的答案</summary>
<p>读取图像的坐标系 ID 并将其追踪到固定帧。如果该路径存在，请检查 TF 是否覆盖图像时间戳以及 RViz 是否遵循相同的时钟。</p>
</details>

相机在仿真时间内以 15 Hz 的频率发布。超过六秒后，时钟会前进三秒。 CameraInfo 的频率约为 7.5 Hz，RGB 的频率约为 3 Hz。你能推断出什么，你会首先改变什么？

<details>
<summary>检查你的答案</summary>
<p>实时系数为 0.5，这解释了每墙每秒大约有 7.5 次到达。额外的 RGB 不足与图像管道或其测量有关。使用 CameraInfo 比较订阅者 QoS 和标头间隙。然后单独改变分辨率并重复。如果实时因素也发生变化，则重新计算新运行的预期到达率。</p>
</details>

## 常见的误解

- 主题发现证明交付。图表可以宣传其 QoS 或执行状态阻止你的订阅者接收样本的发布者。
- 主题速率是摄像机配置的速率。到达率包括模拟速度、出版工作、传输和用户容量。
- 设置 `use_sim_time` 会重写消息标头。它改变了消费者的时钟。出版商仍然选择自己的页眉印章。

## 总结

在信任外部观察之前，请证明时钟权威、样本交付和采集时间的变换查找。将时间戳间隔与在一次有意的费率变化下的到达时间进行比较。这两个测量值告诉你接下来要检查图表的哪一部分。

继续[模拟实验](/zh/notes/isaac-experiments/) 并在将相机连接到 capstone 臂时使用这些检查。
