---
title: "ROS 2 节点与话题"
topic: "ROS 2"
order: "060"
description: "跟踪从发布者到其订阅者的类型化消息流。"
prerequisites: "对于实验室：来源 ROS 2 Jazzy shell。阅读没有 ROS 的设计部​​分。"
minutes: 40
---

## 为什么要将一个机器人程序拆分为节点？

仿真器可以计算读数、绘制场景并在单个进程内控制机器人。为什么要将读数移至消息总线？因为可视化工具、实验记录仪和控制器具有不同的寿命和故障模式。你应该能够添加记录器或更换显示器，而无需编辑传感器生成器。代价是名称、模式、传递和时间戳成为显式接口而不是隐式函数参数。

考虑虚拟范围传感器。即使可视化暂停，它也可能以 10 Hz 运行。如果显示器通过调用仿真器进程内的函数来提取数据，则它会耦合到该进程及其实现。如果它订阅，它可以按照自己的时间表运行。作为交换，它需要一个明确的答案：“我可以错过哪些阅读内容？多陈旧才算太陈旧？”

## 基本原理

ROS 2 节点是一个计算单元。主题是特定类型消息的命名通道。发布者将消息发送到主题而不命名消费节点。多个订阅者可以观察同一个流，只要他们的通信设置兼容。

```text
 simulator node ── publishes ──▶ /scan : sensor_msgs/msg/LaserScan
                                    ├─▶ visualization
                                    ├─▶ logger
                                    └─▶ motion planner (if explicitly wired)
```

主题不一定是共享的 Python 对象，也不一定是中央队列。节点通过其中间件配置发现端点。名称和类型标识兼容的候选者；服务质量 (QoS) 描述了交付期望。应用程序仍然需要语义。例如，`LaserScan`，包括范围值、角度信息和标头； “浮点数组”不会告诉你如何将索引转换为方向。

以主题为导向的设计适合重复的独立观察。需要确认的命令需要明确的语义。校准 ID 的同步请求比轮询数据主题更适合服务。具有反馈的长时间运行的模拟抓取和适合动作的结果。 [通信讲座](/zh/notes/ros2-communication/) 构建了这些区别并有意打破了 QoS 匹配。

## 开发流程：使用合成生产者测试图表

第一个里程碑是观察消息，而不是调出机器人或 RTX 仿真器。在安装了 ROS 2 Jazzy 的 Ubuntu 24.04 上，使用与物理机器人隔离的两个 Bash 终端。必须在每个终端中运行相同的设置。如果未安装 Jazzy，请按照[工作空间章节](/zh/notes/ros2-workspaces/) 操作并返回此处。

```bash
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DOMAIN_ID=72 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
unset ROS_STATIC_PEERS
```

如果72被占用，则选择一个未使用的本地域；将该选择应用于两个终端。在终端 A 中运行这个生产者。玩具有效负载故意是一个字符串。它是一个传输探针，而不是建议的扫描仪模式。

```bash
ros2 topic pub --rate 2 /study/sample std_msgs/msg/String '{data: synthetic}'
```

在 B 中，检查接口，然后观察流：

```bash
ros2 interface show std_msgs/msg/String
ros2 topic list -t
ros2 topic info -v /study/sample
timeout 6s ros2 topic echo /study/sample std_msgs/msg/String --once
```

预计有一个发布者和收到的 `data: synthetic`。使用相同的设置在第三个 shell 中启动第二个 echo。两路回波均可独立接收；第一个不会从共享队列中删除消息。停止终端 A。随后启动的 echo 不会仅仅因为它知道消息类型而获得新样本。等待超时，而不是将空闲订阅误认为崩溃。

现在，在终端 B 中使用不同的域运行一个命令。如果终端 A 正在域 72 中主动发布，则 B 应该在域 73 中接收不到任何内容。将 B 切换回来以证明发布者和模式没有更改。匹配域是本实验中的发现先决条件，而不是授权机制。

```bash
ROS_DOMAIN_ID=73 timeout 6s ros2 topic echo /study/sample std_msgs/msg/String --once
```

该探针非常有用，因为它将图形配置与传感器代码隔离。如果有效而 `/scan` 无效，请一次更改一层。检查仿真器是否正在播放并提供发行商。然后检查消息类型和 QoS。最后，即使在样本到达后也要检查捕获时间和帧。成功的回声证明了对该回声的传递，而不是对另一个消费者的有效性。

## 算例

假设仿真器在 `/scan` 上发布了虚拟距离传感器。在已为仿真器的 ROS 2 环境配置的终端上，检查主题而不向机器人发送命令：

```sh
ros2 topic list -t
ros2 topic info -v /scan
ros2 topic echo /scan --once
```

第一个命令列出可见主题及其类型。第二个显示端点及其服务质量 (QoS) 设置。最后等待一条消息。如果你没有在 `/scan` 上发送的仿真器或发布者，则不会有要打印的扫描。

如果主题可见但没有任何消息到达，请检查发布者是否正在主动发送、主题名称和消息类型是否匹配以及订阅者请求的 QoS 是否与发布者提供的 QoS 兼容。

如果 `/scan` 到达，请选取一个样本并检查标题、角度增量、有效范围限制和数组长度。索引 5 处的读数对应于 `angle_min + 5 × angle_increment`，而不是任意角度。然后角度和距离描述了传感器框架中的一个点；在基本框架中使用它需要在扫描时转换数据。这一进程将传输、模式、几何和感知分开，而不是尝试从空白显示中调试所有四个。

## 尝试一下

可视化节点和记录器都需要相同的模拟扫描流。你应该仅为记录器创建第二个主题吗？

<details>
<summary>检查你的答案</summary>
<p>不需要。两个节点都可以订阅 /scan。每个订阅都需要兼容的消息类型和 QoS。</p>
</details>

## 转账练习：已收到但无法使用

扫描以预期速率到达，但当机器人静止时，显示器在机器人后面绘制了一个障碍物。你会从提高发布率开始吗？

<details>
<summary>检查你的诊断计划</summary>
<p>不会。定期接收速率可建立传输。验证哪个扫描角度对应于直线前进，检查割台的坐标系 ID，然后使用已知障碍物检查传感器到底座的旋转。如果仅在移动时出现错误，还要比较采集和转换时间。</p>
</details>

## 弘扬什么

- 将生产者与独立消费者分开，但明确类型、时间和交付偏好。
- 在添加仿真器之前，使用合成节点来证明图形管道。
- 使用收到的消息作为传输的证据。分别验证框架、单位和新鲜度。

## 阅读下一篇

- [ROS 2 Jazzy：理解主题](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html)
- [Jazzy LaserScan 消息定义](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/LaserScan.msg)
