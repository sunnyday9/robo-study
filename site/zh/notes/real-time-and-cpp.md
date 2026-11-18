---
title: "ROS 2 的实时预算与 C++"
topic: "Field engineering"
order: "121"
description: "将控制率转化为截止日期，测量发布和执行延迟，并确定 C++ 和看门狗的归属。"
prerequisites: "机器人系统和嵌入式控制，以及对 ROS 2 主题的基本熟悉。该实验室需要 Python 3。"
minutes: 50
---

## 费率告诉你何时开始规划预算

以 200 Hz 运行的移动机器人速度控制器的周期为 5 ms。如果传感器读取开始较晚，则即使控制器本身只需要 1 毫秒，更新也可能会在 6 毫秒后完成。在这些额外的毫秒内，驱动器保留先前的输出，并且下一次计算可能会以不同的采样间隔开始。良好的平均速率可以隐藏这些事件。为循环指定最后期限，并在错过时给出指定的响应。软性错过最后期限可能会降低质量。对于严格的截止日期，任何错过都会违反要求，并且时间参数需要的不仅仅是基准。

对于周期 `k`，令 `rₖ = r₀ + kT` 为其在单调时钟上的预期发布，`sₖ` 为实际开始，`fₖ` 为完成，`D` 为其相对截止时间。发布延迟为 `sₖ − rₖ`，已执行执行时间为 `fₖ − sₖ`，响应时间为它们的总和 `fₖ − rₖ`。将最后的数量与 `D` 进行比较。实际起始间隔 `sₖ − sₖ₋₁` 对照 `T` 测量周期间抖动。标记你所说的抖动指标。传感器的应用寿命是另一个量。它包括周期开始之前的时间，即使计算达到了自己的截止日期，也可能超出预算。

```text
 One illustrative cycle, elapsed from intended release

 planned        actual       read        control        output     deadline
 release        start        done        done           applied    for cycle
 0 ms --------- 0.7 -------- 1.5 ------- 2.5 ---------- 3.7 ------ 5.0 ms
       0.7 wait      0.8 I/O      1.0 math      1.2 commit    1.3 slack
```

时间线花费了 5 毫秒中的 3.7 毫秒，其中包括调度程序等待。预算审查可以准确地将这些量分配给唤醒、输入、计算和输出，并保留 1.3 毫秒作为余量。这些数字是说明性的。在设计审查中，将每个阶段限制在预期负载下，并检查如何获得限制。仅当测量边界包括设备时，以 3.7 ms 完成的软件写入才是物理应用的证据。对于示教移动机器人，在 MCU 上保留 5 ms 轮循环和 50 ms 命令租用。然后主机端测量支持参数的主机部分。

## 在选择语言之前先确定关键路径

使用 Python 探索控制器数学、驱动模拟、检查轨迹并使用 `rclpy` 制作 ROS 图原型。保留其测量的时序和运行时间假设满足其要求的组件。对于需要更严格地控​​制数据表示、分配和线程行为的 CPU 工作，请将热路径置于 C++ 中并在主机边界使用 `rclcpp`。将控制更新保持为具有显式输入、输出、状态和经过时间的小函数。为它提供与 Python 参考相同的固定装置。在比较性能之前检查符号、单位、饱和度、重置行为和容差。

`rclcpp` 订阅通过执行器接收数据，该执行器为订阅、计时器和其他实体安排回调。在单个执行程序线程上，长回调可能会延迟就绪计时器。在多线程执行器中，互斥组中的回调仍然相互排除。布置组和线程，并记下它们共享的状态。一种布局为时间敏感循环提供有界的最新样本切换，并将报告和服务调用移动到另一个上下文。有界切换在满时需要明确的规则，并且控制器在读取时仍然检查样本年龄。如果端到端记录中的延迟重叠，请分别衡量中间件交付、回调调度和切换的成本。 [ROS 2 Jazzy 执行器文档来源](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/Concepts/Intermediate/About-Executors.rst) · [ROS 2 通讯](/zh/notes/ros2-communication/)

在定时路径之前初始化并预分配。审核调整大小操作、消息构建和发布、格式化日志记录、文件 I/O 和锁定。即使 CPU 使用率较低，等待低优先级工作持有的锁的高优先级线程也可能会错过最后期限。 ROS 2 实时教程指出页面错误、动态分配和释放以及无限期阻塞同步是不确定性的根源。在受支持的 Linux 系统上，PREEMPT_RT 使更多内核工作可抢占，包括许多中断工作。在专用系统上测试调度更改之前，与平台所有者一起审查优先级和竞争工作负载。 C++ 和 PREEMPT_RT 各自让应用程序负责有限的工作和目标配置的证据。 [ROS 2 Jazzy实时教程源码](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/Tutorials/Demos/Real-Time-Programming.rst)·[Linux PREEMPT_RT理论](https://docs.kernel.org/core-api/real-time/theory.html)

## 实验室 — 测量周期循环的开始和结束

另存为 `timing.py`。在装有 Python 3.7 或更高版本的普通笔记本电脑上运行 `python timing.py`，然后运行 ​​`python timing.py --delay`。第二次运行显式地停止几个周期以建模等待外部依赖项。两次运行都使用 `monotonic_ns()` 来计算已用时间，并针对绝对预期释放时间进行睡眠，因此较晚的周期不会改变计划的其余部分。 `sleep` 由于日程安排可能会延迟返回。该脚本会删除与之前的工作交叉的版本并单独对它们进行计数。这些调用在普通主机调度程序上运行。 [Python时钟和睡眠文档](https://docs.python.org/3/library/time.html)

```python
import math
import sys
import time

PERIOD_NS, SLOTS = 5_000_000, 200
inject_delay = "--delay" in sys.argv
release_zero = time.monotonic_ns() + PERIOD_NS
records = []
slot = skipped = 0

while slot < SLOTS:
    release = release_zero + slot * PERIOD_NS
    remaining = release - time.monotonic_ns()
    if remaining > 0:
        time.sleep(remaining / 1_000_000_000)
    start = time.monotonic_ns()
    sum(i * i for i in range(200))
    if inject_delay and slot % 40 == 10:
        time.sleep(0.013)
    finish = time.monotonic_ns()
    records.append((slot, start - release, finish - start, finish - release))
    next_release = (finish - release_zero + PERIOD_NS - 1) // PERIOD_NS
    next_slot = min(SLOTS, max(slot + 1, next_release))
    skipped += next_slot - slot - 1
    slot = next_slot

late_slots = [row[0] for row in records if row[3] > PERIOD_NS]
for name, column in (("start lateness", 1), ("work elapsed", 2), ("response", 3)):
    values = sorted(row[column] for row in records)
    p99 = values[math.ceil(0.99 * len(values)) - 1]
    print(f"{name}: p99 {p99 / 1e6:.3f} ms, max {values[-1] / 1e6:.3f} ms")
print(f"late completed slots: {late_slots}")
print(f"{len(late_slots)} late completions + {skipped} skips / {SLOTS} releases")
```

在具有足够精确睡眠的安静机器上，预计基线很少会出现偏差。如果所有五个注入的停顿都运行，则每个停顿都需要比其 5 毫秒截止时间更长的时间，并且至少会跳过两个版本。预计后期列表中的槽号接近 10、50、90、130 和 170，当所有注入运行时至少会跳过 10 个。调度程序峰值可能会增加未命中或跳过注入时隙。在代表性负载下重复并保留每次运行的结果。如果开始迟到时间增加而已用工时保持不变，则调查调度延迟。如果仅过去的工作增加，请将其分为计算时间、等待时间和提交时间。已消耗的工作时间包括线程在工作期间被抢占的任何时间，因此仅靠长样本无法确定原因。该脚本故意分配测试记录，没有 ROS 运行时，并且不执行任何电机命令。

## 确定延迟更新失败的原因

执行积压的旧更新可能会放大故障。对于最新值控制器，请跳过过时的版本并在下一次计算之前检查新输入。记录跳过的发布和连续的错过。让接收 MCU 在其自己的时钟上强制执行命令新鲜度。单独考虑使用硬件看门狗来防止 MCU 进度丢失。在所需的工作取得进展后，而不是通过可以通过死锁控制器继续运行的计时器中断来馈送它。看门狗复位会改变系统状态。查看默认输出、初始化、故障报告和受监督的重启顺序。保护路径仍然需要针对特定​​机器进行审查。

## 练习

1. 研究回归。基线在 p99 处达到 0.8 毫秒开始延迟和 0.4 毫秒工作。加载运行分别达到 3.4 毫秒和 0.5 毫秒。哪个衡量标准应该指导你的第一次改变？

<details>
<summary>解决方案</summary>

首先测量回调进入之前的等待时间，其中出现较大的变化。比较回调准备时间、调度时间以及在同一重放下与其他工作的重叠情况。直接分析每个样本的响应。总和的 p99 不必等于两个 p99 值的总和。

</details>

2. 测试看门狗独立性。规划器死锁后，主机心跳保持绿色，而发送线程不断发出其最后一个目标。试运行应该暴露什么故障？

<details>
<summary>解决方案</summary>

当发送者继续时，冻结模拟跟踪中的规划器进度。检查旧的目标数据是否仍然更新接收者的租约。将新鲜度与有效控制进度绑定，并定义重复值何时携带新的有效观测结果。在指定的截止日期之前断言陈旧输出转换，并需要新的会话来恢复。

</details>

## 总结

根据预期发布对每个阶段进行预算，并报告延迟完成和跳过的发布。使用 Python 进行参考和仪器实验，并在测量的关键路径需要控制分配和执行时使用 C++。设计新鲜度检查和看门狗行为，以应对它们应该检测到的故障。
