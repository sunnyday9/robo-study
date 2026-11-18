---
title: "让机器人坐标系和时间保持一致"
topic: "ROS 2"
order: "063"
description: "构建一个小型 TF 树，并在仿真器桥上定义帧、单元和时间戳契约。"
prerequisites: "Jazzy 工作区、键入主题和基本坐标变换。"
minutes: 45
---

## 预测工具提示应该在哪里

检测表明前方有一个点 20 厘米。在相机、手腕或机器人底座之前？如果曝光后手腕转动，控制器应使用哪个方向？图表可以按时提供每个观测结果，但仍然会产生系统性错误的目标。构建一个三框架模型，你可以手动计算其预期坐标。通过单个关节变化，使其工具原点从基座坐标系中的 `[0.2, 0, 0]` 移动到 `[0, 0.2, 0]` 米。然后推理在手腕移动后如何从标记的观测结果中重现任一答案。

## 分离几何、状态和时间

URDF 描述了机器人的运动学模型。链接命名刚体。每个关节指定其父级和子级、零位移时其父级中的关节位姿，以及（对于移动关节）关节框架中的轴。 `sensor_msgs/msg/JointState` 一次为指定的关节提供值。其 `name[i]` 与 `position[i]` 相对应，旋转关节为弧度，棱柱关节为米。明确映射硬件或仿真器名称。一旦另一个生产者或部分联合更新进入图表，单独的数组顺序就不是一个好的标识符。

`robot_state_publisher` 结合模型和关节值，在 `/tf_static` 上发布固定边，在 `/tf` 上发布移动边。为每个孩子提供一位父母，为每条边提供一位预期的出版机构。仿真器可以直接发布变换，如果它拥有并非来自 URDF 的几何体，这会很有用。根据机器人的模型和关节状态计算机器人的变换，为其他工具提供了共享的运动学描述。在一个图中使用这两种方法之前，为每条边选择一个权威。该实验室使用一种模型和一个联合发布者，没有根运动或物理场。 [Jazzy robots_state_publisher](https://raw.githubusercontent.com/ros/robot_state_publisher/jazzy/README.md) · [JointState 定义](https://raw.githubusercontent.com/ros2/common_interfaces/jazzy/sensor_msgs/msg/JointState.msg)

![TF 树，在 /tf 上具有移动的 base_link 到腕部链接边缘，以及固定的腕部链接到 /tf_static 上的工具链接边缘。旋转手腕会改变基座坐标系中的工具位姿。](/assets/ros2-tf-chain.svg)

该图显示了组合的两个不同输入。刀具偏置沿手腕 +X 始终为 0.2 m。移动边缘告诉你手腕 +X 指向底座的哪个方向。围绕 +Z 的正四分之一圈会将 +X 朝 +Y 方向旋转。对于沿工具 +X 也为 0.1 m 的工具点，首先在手腕坐标中添加安装偏移以获得 `[0.3, 0, 0]`，然后在基坐标中旋转到 `[0, 0.3, 0]`。反转变换或在基座坐标系中添加安装偏移会给出不同的答案。

## 向缓冲区询问特定时间的问题

将 `lookup_transform(target, source, time)` 读取为“在某个时间将源中的数据表达到目标中”。此摘录假设正在运行的 tf2 侦听器已填充名为 `buffer` 的 `Buffer`，并且 `observation` 是带标记的工具框架消息。查找检索变换。然后，调用者使用适合消息类型的几何帮助器将其应用于观察的坐标。

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

零请求链的最新可用转换。该观察合约拒绝零，因此未初始化的标记无法默默地触发该行为。这是一个说明性的历史记录，观察者在所有三个转换到达后运行：

```text
ROS time (s)      10.00           10.10             10.20
wrist yaw         0 deg          +45 deg           +90 deg
                  ^                                   ^
              image taken                       latest TF now

tool origin for image stamp 10.00 -> [+0.200, 0,      0] m
tool origin for latest lookup    -> [0,      +0.200, 0] m
image taken at 10.05 instead     -> [+0.185, +0.077, 0] m
```

尽管两次查找都能成功，但前两个结果相差约 28 厘米。中间示例使用 22.5 度：将样本包围在同一动态边缘上，tf2 插入平移和方向。它不会推断手腕未来的运动。如果标记比可用转换新，则允许短暂的有限等待 TF 到达。让侦听器的回调在你等待时运行。在单线程执行器中，在查找中阻止订阅可以防止这些回调填充缓冲区。将少量观察排队并在接收回调之外重试，或使用异步转换等待。如果标记早于缓存，请检查处理年龄、缓存历史记录和时钟一致性。丢失的帧或断开的树需要在任一时序修复之前进行拓扑检查。 [Jazzy tf2 缓存](https://raw.githubusercontent.com/ros2/geometry2/jazzy/tf2/src/cache.cpp) · [Jazzy tf2 缓存](https://raw.githubusercontent.com/ros2/geometry2/jazzy/tf2_ros_py/tf2_ros/buffer.py)

如果节点上存在 `use_sim_time`，则其 ROS 时钟遵循 `/clock`。在时钟初始化之前将零视为启动条件。使用 ROS 时间进行采集、变换匹配和测量年龄。使用单调的墙时间截止时间来等待启动，因此暂停的仿真器无法阻止测试超时。观测值和 TF 之间的纪元大小差异通常表明混合系统和仿真时间。在重置期间，清除应用程序队列和缓存的事件状态，并等待新的间隔填充，然后再次使用观察。显式测试暂停和向后跳转。 [ROS时钟设计](https://design.ros2.org/articles/clock_and_time.html)

## 实验室 — 预测组合变换

在三个新 shell 中获取 `~/robo_ws/lab-env.bash`，并在整个实验室中保持系统时间。在 Ubuntu 24.04 上，如果需要，请安装 `ros-jazzy-robot-state-publisher` 和 `ros-jazzy-tf2-ros`。将此完整的 URDF 保存为 `~/robo_ws/tabletop.urdf`。手腕开始与底座重合，因此工具安装座是唯一的平移。 [Jazzy 终端设置](/zh/notes/ros2-workspaces/)

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

如果 `check_urdf` 可用（Ubuntu 24.04 上为 `liburdfdom-tools`），请运行 `check_urdf ~/robo_ws/tabletop.urdf`。验证解析器是否将 `base_link` 视为根，将手腕和工具视为连续的子项。解析的树仍然可以具有反向的关节轴或以厘米为单位输入的测量偏移。使用数字检查点来捕获这些错误。 [Ubuntu Noble URDF 工具](https://packages.ubuntu.com/noble/liburdfdom-tools)

在三个单独的终端中运行以下命令。联合出版商使用其 ROS 时钟为每个合成样本打上标记。这些命令在不模拟物理或命令硬件的情况下练习运动学。

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

在零时，预计平移接近 `[0.2, 0, 0]` m，偏航接近零。停止 B 并使用 `position: [1.57079632679]` 重复其命令，使 A 和 C 保持运行。预计平移接近 `[0, 0.2, 0]` m，偏航接近 +90 度。记录 C 为每个设置打印的内容，包括标记。此处使用的 `tf2_echo` 报告最新的可用转换。其结果验证了两种稳定配置。上面的特定时间查找提出了一个不同的问题。

如果 C 无法解析整个链，请使用 `ros2 run tf2_ros tf2_echo wrist_link tool_link` 单独探测安装座。你可以在启动后使用 `ros2 topic echo /tf_static --qos-durability transient_local --once` 检查固定边沿。如果安装工作正常，请在单独的外壳中检查 `ros2 topic echo /joint_states --once` 是否有新印记、准确的接头名称和弧度值。然后检查 `/tf` 的底座到手腕边缘。如果链解析但四分之一圈落在基础 `-Y` 上，则从关节轴的符号和变换查询的方向开始。如果它落地离基地很远，请检查偏移量和单位。在编辑模型之前，每个探针都应缩小解释范围。检查后停止所有三个进程。 [Jazzy 主题发布者源码](https://raw.githubusercontent.com/ros2/ros2cli/jazzy/ros2topic/ros2topic/verb/pub.py) · [Jazzy tf2_echo 源码](https://raw.githubusercontent.com/ros2/geometry2/jazzy/tf2_ros/src/tf2_echo.cpp)

## 编写仿真器桥合约

对于[桌面 capstone](/zh/notes/capstone-tabletop/)，在连接软件之前指定每个桥接口。

| 领域 | 记录并验证 |
| --- | --- |
| 架构和方向 | 主题/类型、发布者、预期速率和 QoS |
| 几何 | 坐标系 ID、轴、单位、关节名称和四元数顺序 |
| 时间 | 在采集或模拟步骤中标记，选择一个 `/clock` 权限，并定义重置行为 |

对于 Isaac Sim 6.1.0 Franka 桥，在使用检测选择命令之前，针对实际发布的轴运行已知角度测试。单独验证相机光轴，因为光学框架使用 +Z 向前、+X 向右和 +Y 向下。获得观测结果后，对观测结果进行标记，在该标记处匹配 TF，并将观测结果与随后选择的操作配对。保留这两个时间以供以后检查。 Python 3.12 中的 LeRobot 0.4.3 PushT 实验室是一项单独的任务。通过 ROS 共享坐标不提供将 Franka 演示导出到学习环境所需的显式适配器。 [ROS坐标约定](https://www.ros.org/reps/rep-0103.html)

## 练习

1. 预测新的方向。将手腕命令更改为 `-1.57079632679` rad。在运行之前，预测基座坐标系中的工具原点。然后预测沿工具+X 0.1 m 的点的坐标。

<details>
<summary>解决方案</summary>
<p>负四分之一圈将手腕 +X 映射到底座 -Y。原点位于 [0, -0.2, 0] m。该点位于 [0, -0.3, 0] m。使用 tf2_echo 检查原点，然后对点应用相同的变换，而不是将平移读取为点坐标。</p>
</details>

2. 调试具有两个时钟域的捕获。重置后近 3.5 秒摄像机观测结果带有标记。 TF 仅适用于系统纪元时间戳。最新的查找似乎有效。什么才能使精确时间测试通过？

<details>
<summary>解决方案</summary>
<p>验证两个生成器使用相同的采集时钟，并修复 TF 生成器以从仿真时间线中标记。 Check that sim-time consumers receive the single intended clock, then take a fresh observation after reset and verify that the dynamic TF interval brackets its stamp.最近的查找会跳过时间契约，并且可以在观察后默默地返回位姿。</p>
</details>

## 常见的误解

- 有效的 URDF 可保证正确的几何形状。解析检查模型结构。验证已知联合值的符号和大小。
- 静态变换使组合位姿静态。该安装座固定在其父级中。变化的上游边缘会改变底座的姿态。
- 每个推断错误都意味着缓存太小。将请求的标记与间隔的两端进行比较并检查时钟域。

## 总结

计算预期的位姿，分别验证静态边缘和移动边缘，并改变一个关节以确认构图。在使用控制点之前，请验证该链是否在预期时钟下的采集时间解析。

接下来，将这些合约保存在[ROS 2包和测试](/zh/notes/ros2-bags-and-testing/)中。
