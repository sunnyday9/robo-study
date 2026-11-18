---
title: "网络、DDS 与数据存储"
topic: "Infrastructure"
order: "102"
description: "诊断 ROS 2 发现、预算摄像机流量并保留重放所需的文件和时钟。"
prerequisites: "了解 ROS 2 发布者、订阅者和主题类型"
minutes: 50
---

## 发现、交付和隔离

你的录音机看到摄像机主题，但袋子有间隙。队友将包复制到笔记本电脑上并且无法回放。这些失败需要单独的证据。网络必须发现并匹配端点，记录器必须承受传入负载，并且导出的工件必须使用足够的上下文进行恢复以解码其内容。

争取三个可观察到的结果。在目标域上接收合成消息，并在仅更改订阅者的域后观察到超时。在请求两个摄像机之前计算捕获预算，然后在有界运行期间比较实际的发布者和接收者计数。最后将样本恢复到干净的目录中并检查其字节和内容。这些检查会告诉你首先要处理哪种故障。

DDS 是大多数 ROS 2 配置使用的中间件。其参与者发现其他参与者，然后尝试按主题、类型和兼容的服务质量 (QoS) 来匹配发布者和订阅者。 `ROS_DOMAIN_ID` 将参与者分组到逻辑网络中。匹配的 ID 只是其中一项要求。网络可达性、中间件配置和匹配的端点设置也很重要。

使用分配的实验室域并将发现限制在本地计算机上进行回放。通过 Jazzy 基于 DDS 的默认中间件且没有静态对等点，`ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` 将自动发现限制在本地计算机上。相同的旋钮不适用于 `rmw_zenoh`。域 ID 不提供身份验证。将物理控制器保留在具有防火墙规则的单独网段上，并使用经批准的遥测网关或经过检查的文件导出来移动数据。 Docker 网络或 WSL2 NAT 是一个单独的边界。 Windows WSL 镜像网络支持多播，并且防火墙规则仍然适用。 [Jazzy 发现设置](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Advanced/Improved-Dynamic-Discovery.rst)、[ROS 域 ID](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Domain-ID.rst)、[Microsoft WSL 网络](https://learn.microsoft.com/en-us/windows/wsl/networking)。

![真实的机器人和记录器共享一个隔离的机器人网络。审阅的文件导出后会转移到实验室，在那里本地回放为分析订阅者提供信息。没有实时 DDS 路由加入网络。](/assets/infra-dds-boundaries.svg)

从左到右阅读该图。记录器位于生产者附近，因此高速率样本保留在捕获部分。只有经过审核的导出才会进入回放实验室。域更改有助于防止共享网段上的意外发现。防火墙和网络边界控制哪些机器可以通信。保持本地回放还意味着可以在不访问机器人的情况下调查丢失的消息。

## 实验室·找到第一个打破的边界

**Design.**从一个小字符串主题开始，因此传输负载和磁盘吞吐量与测试无关。在 **same**预配置的 Jazzy Linux 或 WSL2 环境中使用两个新的 Bash 终端，与物理机器人断开连接。在两者中运行此序言。使用默认的 DDS 中间件及其默认传输配置。

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
unset ROS_STATIC_PEERS
```

在终端 A 中，启动一个无害的合成发布程序。练习结束后按 Ctrl+C 停止。

```bash
ros2 topic pub --rate 2 /infra_probe std_msgs/msg/String '{data: probe}'
```

**观察并改变。**在终端 B 中，将匹配的域与故意不同的域进行比较。该前缀仅更改第二次调用的域。以下结果是对此设置的预测。

```bash
ros2 topic echo /infra_probe std_msgs/msg/String --once --timeout 8
ROS_DOMAIN_ID=43 ros2 topic echo /infra_probe std_msgs/msg/String --once --timeout 8
```

| 观察 | 下一步检查 |
| --- | --- |
| 域42打印`data: probe`，域43超时 | 预计。恢复通信匹配域并保留网络边界隔离。 |
| 两者在同一主机上都超时 | 检查发布者是否仍在运行，然后在两个 shell 中比较域、中间件、发现范围和主题/类型。 |
| 本地测试成功，跨主机发现失败 | 检查容器或 WSL 网络模式、接口、多播和防火墙策略。如果多播不可用，请使用授权实验室网段上记录的对等配置。 |
| 端点可见，但交付停滞 | 检查 `ros2 topic info -v /infra_probe` 提供和请求的 QoS。可靠的订阅者无法与尽力而为的发布者相媲美。检查 QoS 后的发布速率和传输负载。 |

**调试并迭代。**恢复域42并使用`ros2 topic info --no-daemon -v /infra_probe`直接查询本地图。当订阅者仍在等待检查两个端点时，从具有相同前导码的第三个 shell 运行它。在衡量交付之前，请检查生产者数量、类型以及所提供的策略与所要求的策略。使用不同设置运行的守护进程可能会使图形查询错误地表示你正在测试的 shell。 [爵士主题信息来源](https://github.com/ros2/ros2cli/blob/jazzy/ros2topic/ros2topic/verb/info.py)。

一旦域 42 再次通过，就隔离 QoS 故障。首先在原始发布者上使用 `--qos-reliability reliable` 运行 echo。然后使用相同的命令加上 `--qos-reliability best_effort` 停止并替换发布者。确保订户明确可靠。期望有广告发布商，但没有匹配的可靠交付。仅将订阅者切换到 `--qos-reliability best_effort`，并再次等待消息。在实时感知中，最近的数据可能比恢复每个数据包更重要。对于离线捕获，重传可以提高完整性，但代价是额外的流量、队列和延迟。在决定之前检查录音机和制作人计数器。 [Jazzy QoS 兼容性](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Quality-of-Service-Settings.rst)，[Jazzy 回声选项](https://github.com/ros2/ros2cli/blob/jazzy/ros2topic/ros2topic/verb/echo.py)。

对于允许的实验室网段上的跨主机传输练习，请首先验证接口和可达性。即使单播连接有效，多播发现也可能跨 NAT 或容器桥失败。静态对等点提供明确的发现目标，并需要参与者的可达地址和兼容设置。在发送传感器流量之前跨边界测试相同的小主题。如果在相机传输失败时它通过了，那么这条小消息已经消除了该配置的一般发现失败。

## 确定带宽和存储预算

对于紧密封装的 RGB8，1280 × 720 × 3 每帧提供 2,764,800 字节。乘以 30 帧/秒即可得到 82,944,000 字节/秒，大约为 **83 MB/s 或 664 Mb/s**（使用十进制单位）。两个此类相机需要 **166 MB/s 或 1.33 Gb/s**的像素有效负载。 1 Gb/s 链路在扣除开销之前最多可承载 125 MB/s。原始的两个摄像头流甚至超出了理想的限制。如果图像具有行填充，请使用每行字节数乘以高度。设计完整路径时包括其他主题、序列化、数据包开销和突发余量。

在 30 分钟时，两个原始流贡献 `165,888,000 × 1,800 = 298,598,400,000` 字节，大约为 **299 GB**。添加 25% 的计划储备，仅针对该捕获即可免费提供大约 **373 GB**。写入包的大小取决于格式和压缩，恢复和上传暂存都可能需要更多空间。在保留或复制之前，以相同的原始速率保持五次捕获大约需要 1.49 TB。估算实时链接、本地写入路径和保留副本的单独预算。

从一台摄像机开始，持续一段有限的时间间隔。记录同一捕获窗口中的生产者计数、接收者计数、记录计数和经过的时间。在不同的终端中，`ros2 topic hz /camera/image_raw` 和 `ros2 topic bw /camera/image_raw` 估计其订阅收到的内容。它们可以增加负载，但不测量电线利用率。记录后与主机接口计数器和 `ros2 bag info <bag-directory>` 进行比较。如果可用，请使用源标记或序列标识符，因为相等的总数可以隐藏重复项。添加第二个流作为唯一更改的输入。如果接收到的计数首先通过链路下降，请检查链路利用率和订户调度。如果接收计数保持不变，但包计数下降，请检查记录器队列和持续的磁盘写入。 [Jazzy 带宽实现](https://github.com/ros2/ros2cli/blob/jazzy/ros2topic/ros2topic/verb/bw.py)，[rosbag2 Jazzy](https://github.com/ros2/rosbag2/blob/jazzy/README.md)。

在源头进行录制将磁盘需求置于摄像机附近，并避免通过受限链路发送原始帧。压缩可减少字节数，但代价是 CPU 或 GPU 工作量、解码延迟以及可能丢失的图像细节。降低帧速率可以立即节省字节，但可以隐藏短接触事件。更改这些选择之一后，重复相同的捕获测试。

## 携带时钟并测试工件恢复

在多主机捕获中，根据时序预算的要求，通过 NTP 或 PTP 使用通用挂钟参考，并记录测量的时钟偏移。保留设备捕获时间戳和接收时间。如果摄像机 A 在参考之前标记事件 4 毫秒，而摄像机 B 在参考之后标记事件 3 毫秒，则即使事件同时发生，记录的标记中也会出现 7 毫秒的差异。保留原始印章并记录任何偏移修正。

对于模拟和重放，请选择一个 `/clock` 源，并在应遵循该源的使用者上设置 `use_sim_time`。根据包及其标题标记选择记录的时钟或玩家生成的时钟。 Jazzy 的 `ros2 bag play <bag-directory> --clock` 排除记录的 `/clock` 并生成重放时钟。在玩之前停止任何仿真器时钟发布者。在解释重放之前，将标头标记与选定的时钟和 TF 进行比较。维持顶点的“先观察后行动”的顺序。 Isaac Franka 捕获和 LeRobot PushT 评估都有自己的工件合约，需要显式适配器才能连接。 [Jazzy rosbag2 播放选项](https://github.com/ros2/rosbag2/blob/jazzy/ros2bag/ros2bag/verb/play.py)。

```text
 Capture host                Replay host
 frame + capture stamp       verified copy + original stamp
    |                             |
    v                             v
 recorder -> bag + metadata -> player -> analysis subscriber
                                          ^
                              one replay clock for ROS time
```

遵循文件路径中的源时间戳。底部的时钟路径让接收节点在重放期间解释时间戳。共享回放时钟保留录音中已经存在的任何未对准情况。

在本地 SSD 上暂存高速写入，然后将完成的工件上传到版本化对象存储。在 Git 中保留带有校验和、存储 URI、许可证和保留的小型清单。将包元数据、块和消息定义保存在一起。保留 USD 阶段及其引用的图层和纹理、包含视频分片和回合索引的数据集以及策略权重及其配置和标准化统计数据。将一个小样本恢复到一台干净的机器上，并验证哈希值、一个解码帧和包的主题元数据。 [rosbag2 Jazzy](https://github.com/ros2/rosbag2/blob/jazzy/README.md)，[OpenUSD资产解析](https://openusd.org/release/api/ar_page_front.html)，[LeRobot v0.4.3中的LeRobotDataset v3](https://huggingface.co/docs/lerobot/v0.4.3/en/lerobot-dataset-v3)。

**Restorerill.**在包含 capstone 的 [验证器](/assets/labs/check_trace.py) 和 [跟踪夹具](/assets/labs/tabletop-trace.csv) 的 Bash 目录中，创建一个清单并模拟将文件下载到新目录中。这需要 GNU coreutils 和 Python 3。保留上传或可信运行清单中的原始校验和。

```bash
sha256sum check_trace.py tabletop-trace.csv > SHA256SUMS
restore=$(mktemp -d)
cp check_trace.py tabletop-trace.csv SHA256SUMS "$restore/"
(cd "$restore" && sha256sum -c SHA256SUMS &&
  python3 check_trace.py tabletop-trace.csv)
```

预计有两个校验和确认和 `OK: 6 rows across 2 episodes`。使用 `printf 'x' >> "$restore/tabletop-trace.csv"` 将一个字节附加到 **恢复的副本**。重复该子 shell，并期望在 Python 运行之前校验和失败。将原始跟踪复制回来并重复以恢复。此练习将传输完整性与格式可用性分开。对于真实包，验证其固定对象版本和清单，运行 `ros2 bag info`，并在回放主机上解码一条消息。仅可读的主题清单就可以使摄像机解码和回放时间不受检查。

## 练习

<details>
<summary>自检 · 两台摄像机均发现成功，但一台录像机丢帧。更改域名会有帮助吗？</summary>
<p>更改域会更改发现组。测量摄像机总负载、录像机吞吐量和跌落情况。如果两个原始流使链路饱和，请在源附近进行记录，降低速率或分辨率，或者使用压缩并再次测量。</p>
</details>

<details>
<summary>传输 · 两个 15 Hz 的 720p RGB 流能否共享链接并容纳 150 GB 30 分钟？</summary>
<p>将速率减半后，总共可获得约 664 Mb/s，低于理论 1 Gb/s 容量。测量流和其他流量以确认净空。仅像素数据就总计约 149.3 GB。在保留 25% 的情况下，恢复空间之前预算约 187 GB。使用更大的体积、缩短运行时间或测量可接受的压缩模式。检查 15 Hz 是否仍能捕获你需要的事件。</p>
</details>

## 常见的误解

- **“列出的主题证明订阅者可以接收它。”**检查类型以及提供的 QoS 与请求的 QoS，然后观察示例。
- **“带宽探测报告链路利用率。”**它报告探测订阅的速率。与接口计数器和生产者计数进行比较。
- **“对象存在，因此备份有效。”**恢复它并验证字节、依赖关系和解码内容。

## 总结

使用小消息确认发现，然后验证端点匹配并分别调整链路和磁盘的大小。在更换网络或记录器之前测量计数差异的位置。保留源时间戳和工件依赖性，以便回放可以证明录制仍然可用。

在移动到 [桌面顶点](/zh/notes/capstone-tabletop/) 中的模拟拾放之前应用回放边界和恢复检查。
