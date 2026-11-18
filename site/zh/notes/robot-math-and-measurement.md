---
title: "机器人软件中的数学、单位与测量"
topic: "Robotics fundamentals"
order: "006"
description: "将原始测量结果转换为物理单位，区分数值误差和传感器误差，并构建小型接口测试。"
prerequisites: "第一个 Python 机器人循环；基本代数。"
minutes: 55
---

## 为什么要从测量开始？

大多数机器人数学都是从界面开始的。编码器并没有说“向前行驶 6.3 厘米”；它报告计数。时间戳没有说明它是否来自传感器、主机或仿真器。你的第一项工作是将每个数量转换为估算器和控制器可以解释并保留足够的信息来调试错误的转换。

我们的目标：给定三个编码器样本，计算增量速度，拒绝损坏的时间戳，并解释此计算仍然无法确定物理运动的内容。

## 建立维度模型

假设车轮半径为 0.05 m，编码器每转一圈可解码 1,000 个计数。如果这些计数是在电机轴上测量的，请首先通过齿轮比进行转换，并检查驱动器如何定义计数。对于实验室：

```text
 raw ticks → difference / counts per revolution → revolutions
     → × (2π radians / revolution) → wheel angle change [rad]
     → × radius [m] → wheel travel [m]
     → / measured elapsed seconds → wheel speed [m/s]
```

对于 0.1 秒内计数 200 次，轮子转动五分之一转，大约 1.257 rad。理想行程约为 0.0628 m，估计速度为 0.628 m/s。车轮行程不会自动发生世界坐标系位移。当底盘几乎不移动时，打滑的轮子可以报告相同的计数。

决定边界处的输入/输出约定。将距离以米为单位，将速率以适当的单位表示，将角度以弧度表示以便计算，并在矢量旁边保留坐标系名称。 [ROS REP 103](https://www.ros.org/reps/rep-0103.html) 记录了常见的 ROS 单位和坐标约定，包括右手坐标系。系统仍然需要记录它自己的轴和外部参数。

## 你将再次使用的号码

| 概念 | 机器人的使用 | 最低检查项 |
| --- | --- | --- |
| 向量和范数 | 位移、速度、残余震级 | 仅在转换为共享框架和单位后减去 |
| 点积 | 投影或对齐 | 一个带有自身的单位向量给出 1 |
| 矩阵 | 改变基础；近似状态或错误如何演变 | 形状匹配，身份是有意义的基线 |
| 衍生品 | 估计速度或对变化进行建模 | 差值除以经过的时间；检查噪音和间隔 |
| 整合 | 累积速度或角速率 | 乘以经过的时间；检查漂移和步长灵敏度 |
| 均值和方差 | 将持久偏移与分散分开 | 报告样本数量和条件；方差不编码固定偏差 |

接下来的章节将在上下文中教授这些概念。在编码之前你不需要完成单独的数学课程。如果结果有意外的单位，请将它们写在每个中间值旁边。如果答案取决于角度符号，请测试一些简单的东西，例如 90° 转弯，而不是一般的三角示例。

## 履行并检查合同

此可运行示例假设展开计数并在一个时钟上单调递增采集时间戳。它会引发错误，而不是猜测这些假设何时失败。

```python
from math import isclose, tau


def wheel_speed(previous, current, radius=0.05, counts_per_rev=1000):
    previous_ns, previous_count = previous
    current_ns, current_count = current
    elapsed_s = (current_ns - previous_ns) / 1_000_000_000
    if elapsed_s <= 0:
        raise ValueError("acquisition timestamps must increase")
    if radius <= 0 or counts_per_rev <= 0:
        raise ValueError("invalid encoder calibration")
    turns = (current_count - previous_count) / counts_per_rev
    return turns * tau * radius / elapsed_s


samples = [(0, 0), (100_000_000, 200), (220_000_000, 440)]
speeds = [wheel_speed(left, right) for left, right in zip(samples, samples[1:])]
assert all(isclose(speed, 0.2 * tau * 0.05 / 0.1) for speed in speeds)
print([round(speed, 3) for speed in speeds])
try:
    wheel_speed(samples[1], (100_000_000, 400))
except ValueError as error:
    print(error)
else:
    raise AssertionError("bad timestamps were accepted")
```

两个间隔产生相同的速度，约为 0.628 m/s，因为第二个间隔长 20%，并且包含更多 20% 的计数。如果代码假定固定的 0.1 秒间隔，则速度会提高 20%。这看起来像是日志中执行器的不稳定性。在接触电机控制器之前，以完全相同的计数和固定间隔重现错误。

## 单独的采样率、延迟和准确性

采样率告诉你收到不同测量结果的频率；延迟告诉你使用测量值时的时间。读取旧样本的快速回调不是快速传感。对于简单的一计数增量，理想车轮行程的解释约为 0.000314 m。如果存在 0.1 秒的差异，一次计数会使估计速度改变大约 0.00314 m/s。相差 0.01 秒，变化就大了十倍。更快的采样可以提高新近度，同时使朴素导数的噪声更大。

诊断变化时，保持采集时间戳和单调运行时间不同。接收时钟对于本地处理延迟很有用，但减去两个不相关的硬件时钟不会产生有效的延迟。使用记录的同步或偏移估计。在将每个不一致视为随机噪声之前，检查计数器环绕、重置、符号约定、量化、半径不确定性和滑动。

## 练习

读数通过了 0.628 m/s，但卷尺测试显示底盘的移动速度低于预期。代码肯定是错误的吗？

<details>
<summary>分离假设</summary>
<p>否。比较车轮行程、负载下车轮半径以及外部底盘位移。符号或比率错误是可能的，但滑动会使编码器模型在物理上错误，即使其算术通过也是如此。</p>
</details>

你的固件以 80 Hz 的频率发送计数，但你的订阅者报告以 20 Hz 的频率突发。哪个时间戳属于差异？

<details>
<summary>检查两个时序层</summary>
<p>使用传感器斜率的采集时间戳。保留收货时间以调查批次、调度或运输。如果采集样本被丢弃，则计算实际间隔内的差异并报告差距。</p>
</details>

## 保留什么

写下一项有符号单位转换、一项不良样本测试以及一项用于检查物理假设的独立参考。接下来，使用[坐标系](/zh/notes/coordinate-frames/) 将本地测量结果转换为另一个组件可以解释的数量。
