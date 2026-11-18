---
title: "现场调试：用证据定位故障"
topic: "Field engineering"
order: "122"
description: "在更换移动机器人控制器之前，使用分阶段验收计划并追踪第一个破损的边界。"
prerequisites: "机器人系统和嵌入式控制，以及 ROS 时间和经过时间之间的区别。该实验室仅进行 Python 演练。"
minutes: 50
---

## 一次委托一项索赔

<figure class="lesson-figure">
  <a href="/assets/figures/commissioning-ladder.svg"><img src="/assets/figures/commissioning-ladder.svg" width="640" height="494" loading="lazy" decoding="async" alt="四个门：独立审查、模拟、惰性输出试运行以及单独授权的监督物理测试。"></a>
  <figcaption>每个门都需要自己的证据。成功的试运行并不授权进行物理操作。</figcaption>
</figure>

移动机器人在第一次集成测试中转向了错误的方向。工程师可能会反转配置中的电机、更改 TF 框架或向偏航控制器添加减号。每个更改都可能隐藏另一个边界上的错误。调试从安装的机器及其预期用途开始，然后根据已知配置检查逐渐更大的索赔。从一个具有已知预期响应的命令开始。通过转换为车轮目标、接收器接受和测量的响应来跟踪命令。修复第一个违反契约的边界。

在你仍然可以更改设计的同时编写验收计划。确定负责的主管、允许的区域和机器状态、保护功能、中止条件以及推进所需的证据。紧急停止、驱动禁止、正常控制停止和隔离程序是不同的机制，具有不同的效果。物理检查和恢复遵循针对特定机器的批准程序。下面的工作离线运行。 [NASA验证验收规划](https://www.nasa.gov/reference/system-engineering-handbook-appendix/)

| 舞台 | 索赔和证据以推进 |
| --- | --- |
| 在现场程序下隔离驱动的工作台审查 | 记录竣工组件 ID、批准的固件和配置、机械尺寸、标志和传感器/驱动器限制。将零件和校准版本与计划进行比较。使用合成输入和惰性输出接收器进行软件检查。 |
| 闭环仿真 | 根据明确命名的单位、重置条件和时间限制检查前进、左转和输入损失。收集命令与应用的目标轨迹并将模拟位姿与预期方向进行比较。 |
| 集成试运行 | 将版本化的启动配置、命令路由和接受日志与计划进行比较，同时驱动保持隔离。检查启动和丢失数据是否产生预期的抑制状态。 HIL 可以在合格的设置中针对模拟设备执行真实控制器 I/O。 |
| 监督实物验收 | 负责团队在审查前述证据后，授权在受控空间内进行针对机器的测试。他们验证保障措施，定义移动限制，并根据批准的计划测量实际响应和停止间隙。任何未满足的先决条件都会保持舞台。 |

在试运行之前，记录哪种配置可以保证惰性水槽。显示零速度的仪表板不能确定执行器是隔离的。定义中止，包括丢失观察、不确定隔离、更改配置和失去主管控制。保留失败的跟踪并在解决原因后返回到之前的演示阶段。诸如“最后接受命令后 55 毫秒内建模的目标零”之类的说明性门需要其自己的证据。物理停止门分别指定什么算停止、测量不确定性、启动条件以及允许机器穿越的空间。

## 遵循第一个缺失或不一致的观测结果

对于教学移动机器人，正偏航命令要求右轮比左轮转得更快。 `0.20 m/s`、`+0.40 rad/s` 命令为 `2.8` 和 `5.2 rad/s` 提供[机器人系统和嵌入式控制](/zh/notes/robot-systems-and-embedded/) 中定义的几何形状。如果测量的车轮符号和幅度一致，但模拟的位姿向右转，请检查位姿轴和积分几何。如果目标值已在适配器处交换，请在位姿计算之前研究车轮索引。对于桌面手臂，将相同的推理应用于指定的关节目标、标志和框架。

```text
 Symptom: the applied wheel target unexpectedly goes to zero
 |
 +-- Producer emits no new sequence ---> check planner progress and input age
 +-- Sends continue, ingress is quiet --> check link, queues, and ingress logging
 +-- Ingress continues, rejects rise ---> read session, sequence, or range reason
 +-- Valid receives continue -----------> inspect local inhibit and commit state
     |
     +-- Applied target valid, motion differs -> examine feedback or plant evidence
```

该树按边界对观测值进行排序。它缩小了搜索范围，但没有证明原因。例如，没有入口记录可能意味着丢失、接收器重置或丢失的日志条目。记录输入年龄、启动标识、正常运行时间、单调时间戳和时钟 ID、命令会话和序列、接受或拒绝原因、抑制状态、输出目标和带有单位的车轮反馈。包括丢弃日志或覆盖缓冲区计数。使用有界记录器保留故障前窗口并将其写出，远离时间敏感的工作。 ROS `DiagnosticStatus` 提供组件名称、硬件 ID、级别（包括 `STALE`）和键值字段。使用诊断来提高可见性并保持时间关键的联锁路径独立。 [Jazzy Diagnostic状态定义](https://raw.githubusercontent.com/ros2/common_interfaces/jazzy/diagnostic_msgs/msg/DiagnosticStatus.msg)

按会话和顺序连接主机和 MCU 记录。计算接收器稳定时钟的租约。要估计跨机器的单向延迟，你需要一种具有不确定性的可靠时钟映射。否则分别报告发送器间隔和接收器间隔。保留模拟标记以供回放，并记录实际经过的时间作为单独的测量。仿真时钟可以暂停、跳跃或运行得比实际经过的时间更快。 [ROS 2时钟和时间设计](https://design.ros2.org/articles/clock_and_time.html) · [帧和时间](/zh/notes/ros2-frames-and-time/)

## 实验室 — 将丢失的接收与拒绝的命令分开

另存为 `dry_run.py` 并运行 `python dry_run.py healthy`、`python dry_run.py gap` 和 `python dry_run.py reject`。每次运行都会在一个仿真时钟上生成完整的内存中遥测数据。主机每 20 毫秒发送一次，接收方每 5 毫秒评估一次租约。会话从时间零处的第一个有效命令开始。 `gap` 案例会在 40 毫秒后抑制进入，同时主机继续创建命令。 `reject` 案例通过错误的会话传递这些命令。输出是一对数字，表示建模的左目标和右目标（以 rad/s 为单位）。

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("case", choices=("healthy", "gap", "reject"))
case = parser.parse_args().case
trace = []
last_valid = expired_at = None
target = (0.0, 0.0)

for t in range(0, 111, 5):
    if last_valid is not None and expired_at is None and t - last_valid >= 50:
        expired_at, target = t, (0.0, 0.0)
        trace.append((t, "output", f"expired, L/R={target} rad/s"))
    if t % 20:
        continue
    seq = t // 20 + 1
    trace.append((t, "send", seq))
    if t > 40 and case == "gap":
        continue
    trace.append((t, "ingress", seq))
    if t > 40 and case == "reject":
        trace.append((t, "reject", "wrong session"))
    elif expired_at is None:
        last_valid, target = t, (2.8, 5.2)
        trace.append((t, "accept", seq))
        trace.append((t, "output", f"L/R={target} rad/s"))

for t, stage, value in trace:
    print(f"{t:3} ms  {stage:7}  {value}")
if expired_at is None:
    print(f"last accepted {last_valid} ms, no expiry")
else:
    elapsed = expired_at - last_valid
    print(f"last accepted {last_valid} ms, elapsed to zero {elapsed} ms")
```

在健康跟踪中，序列 6 在 100 毫秒时被接受，目标为 `(2.8, 5.2)`。两种故障情况最后在 40 ms 时接受序列 3，并在 90 ms 时产生零，这满足具有 5 ms 裕度的说明性 55 ms 门。在 `gap` 中，第一个缺失边界是序列 4 在 60 ms 处的入口。在 `reject` 中，序列 4 在 60 ms 处到达入口并立即记录 `wrong session`。将这些指纹与输出延迟一起保存在你的验收记录中。添加对最后接受的序列、第一个受影响的序列、拒绝边界报告的原因以及最终状态的检查。实验室对合成数据进行痕迹解释。它没有机器人驾驶员或实际制动的计时模型。

## 练习

**1。修复测量计划。**现场记录显示序列 4 已发送且输出变为零。入口日志存在间隙，但其覆盖记录计数器增加。你能得出什么结论？接下来在演练中你会收集什么？

<details>
<summary>解决方案</summary>

观察发送和输出转换。序列 4 入口结果未知。记录设备启动 ID、每阶段计数和最后序列以及拒绝原因。使用有限的故障前记录重复相同的输入，并确认事件的缓冲区覆盖范围。在确定原因之前，请区分通信间隙和日志记录间隙。

</details>

**2。查看验收记录。**夹具在 90 毫秒处显示零目标，最后一次验收在 40 毫秒处。有人声称机器在链路丢失后 55 毫秒内停止。重写主张并指出缺失的证据。

<details>
<summary>解决方案</summary>

在此装置中，模型在最后接受的命令后 50 毫秒将其目标更改为零。为了测量物理停止，验收计划必须独立定义和观察启动事件，记录校准的速度或位置，定义停止阈值和不确定性，并涵盖批准的情况，例如不同的初始速度和表面。负责的团队负责监督测试。

</details>

## 总结

分阶段进行调试，并在每个边界都有范围狭窄的验收记录。按顺序关联发送、入口、接受和输出。从第一次缺失或不一致的观察中进行诊断，并通过证据的完整性和时间来验证你的结论。
