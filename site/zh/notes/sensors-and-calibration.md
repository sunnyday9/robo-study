---
title: "传感器选型与标定"
topic: "Perception and estimation"
order: "041"
description: "将传感器规格转化为误差预算，然后在 CPU 实验室中将陀螺仪偏差与时间戳偏移分开。"
prerequisites: "基础 Python、坐标系和针孔相机投影。"
minutes: 50
---

## 从漫游者必须做出的决定开始

差动驱动移动机器人需要估计它滚动的距离、转动的距离以及什么占据了它的预定路径。在光滑的地板上，轮子可以转动而无需移动底座。陀螺仪仍然测量旋转，但其小速率偏移会累积成偏航误差。激光雷达可以观察房间，但平面扫描可以穿过低矮障碍物上方或架子下方。通过写下每个传感器直接观察到的内容以及观察到的问题的位置来选择补充测量。

假设模拟移动机器人以 0.5 m/s 的速度移动并以 1 rad/s 的速度转动。 40 毫秒的计时误差对应于 2 厘米的基础平移和 0.04 弧度的旋转。在 2 m 的目标距离处，仅旋转就会使重建点向侧面移动约 8 cm。这为你提供了一种将延迟或同步预算转换为空间预算的方法。对预期任务使用最差的相关速度、范围和测量期限。平均帧速率无法告诉你单个观察的年龄。

## 阅读规格作为测量限制

| 传感器 | 在规格或驱动程序中检查什么 | 在回放或赛程中测量什么 |
| --- | --- | --- |
| 轮编码器 | 每输出转的解码计数、在电机处测量的传动比、采样节奏、计数器宽度和符号 | 每次计数的距离、左/右不对称、重复直线运行和转弯、计数器缠绕、滑动敏感性 |
| 惯性测量单元 | 陀螺仪范围、噪声密度和带宽、温度漂移、样本节奏和轴约定 | 热身后的固定偏差和分散、剪裁、已知旋转期间的轴符号、会话期间的稳定性 |
| 平面激光雷达 | 角度覆盖范围和增量、可用最小/最大范围、范围精度、扫描持续时间、无效返回约定 | 由于材料和角度、盲区、转弯时扫描倾斜而导致回程丢失 |
| 相机 | 分辨率、视野、曝光时间、滚动或全局快门、帧速率和时间戳语义 | 模糊、丢帧、边缘重投影残差以及深度有效性（如果存在深度流） |

对于 0.04 m 的车轮半径和车轮每转 2048 个解码计数，一个计数对应于沿车轮圆周的约 0.123 mm。这就是理想滚动下的量化。轮胎压缩、不正确的半径和打滑会产生更大的行驶误差。对于激光雷达，相距 0.5° 的相邻光束在 2 m 处相距约 17 mm。即使具有出色的测距精度，狭窄的特征也可能落在它们之间。对于焦距为 600 px 的理想相机，2 m 处的 20 mm 物体在光轴附近跨度约为 6 px。检查探测器输入分辨率和传感器分辨率下的表观尺寸。

在界面上指定名称和单位。 ROS 风格的 `base_link` 通常使用 x 向前、y 向左、z 向上。相机光学框架使用 x 向右、y 向下、z 向前。 ROS `Imu` 消息表示角速度（以 rad/s 为单位）和加速度（以 m/s² 为单位）。其全零协方差表示未知的协方差。将单位、原始数据与过滤数据以及时间戳的含义视为驱动程序合同的一部分。 [ROS REP 103](https://github.com/ros-infrastructure/rep/blob/master/rep-0103.rst) · [ROS Jazzy IMU 消息](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/Imu.msg)

## 独立的几何形状、时序和重复性

```text
Raw samples + acquisition timestamps
  |
  +-- Intrinsics: decode the sample in sensor coordinates
  |               e.g. pixels to rays, counts to wheel angle
  +-- Extrinsics: express sensor geometry in the base frame
  |               p_base = R_base_sensor p_sensor + t_base_sensor
  +-- Time:       place the sample on the estimator's clock
                  then look up moving transforms at that time
```

每个更正都回答了关于同一观察的不同问题。固有校准可识别内部参数，例如焦距比例和镜头畸变，或 IMU 轴比例和偏移。使用已知的平面相机目标，在整个图像上展开观察并改变距离和方向。适合一组视图，然后按位置检查保留的像素残差。外部校准估计帧之间的刚性变换。相机校准可以估计每个图像的目标到相机的变换。相机到底座的安装仍然需要与底座具有独立的几何关系。记录变换方向并使用手动计算点进行验证。 [OpenCV相机标定模型及API](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)

对于时间校准，请确定哪个时钟标记了采集以及它如何映射到参考时钟。接待时间包括交通和调度延误。恒定的偏移量可以在短时间内调整稳定的时钟。根据经过时间绘制残差以查找时钟漂移，并根据运动绘制残差以查找采集或时间戳错误。检查样品是否一起采集。 ROS `LaserScan` 标记指的是第一条射线，`time_increment` 给出了射线之间的间隔。 Kalibr 记录的相机 - IMU 工作流程根据记录的数据估计空间和时间校准。 [ROS LaserScan消息](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/LaserScan.msg) · [Kalibr相机-IMU标定](https://github.com/ethz-asl/kalibr/wiki/camera-imu-calibration)

对于使用可信参考 `r` 的测量，计算残差 `e = measured - r`。在这些条件下，均值估计存在偏差。样本方差 `sum((e - mean(e))²)/(n - 1)` 测量值围绕平均值分散，测量单位为平方。紧密的簇可能与参考相距甚远。检查样品的重复性，然后在重新启动或重新安装后重新进行测量，以查看校准传输的情况。温度变化较大，建议在读数的同时记录温度。参考不确定性为你可以推断的内容设定了底限。

## 实验室：区分陀螺仪偏差和延迟时间戳

将其保存为 `sensing-calibration.py` 并运行 `python sensing-calibration.py`。合成陀螺仪延迟采样 40 毫秒。参考提供夹具中任何时间的偏航率。前 100 个样本是静止的，然后模拟移动机器人改变其转弯速率。在一个移动片段上以 1 毫秒为步长拟合候选偏移，并在后面的片段上评分。更正约定为 `acquisition = stamp - offset`。

```python
from math import sin, sqrt
from random import Random
from statistics import mean, stdev

rng = Random(41)


def reference(t):  # rad/s, with t in seconds on the reference clock
    s = max(0.0, t - 1.0)
    return 0.60 * sin(3.0 * s) + 0.25 * sin(7.0 * s)


samples = []
for i in range(600):
    t = i * 0.01
    rate = reference(t) + 0.035 + rng.gauss(0, 0.004)
    samples.append((t + 0.040, rate))

stationary = [rate for _, rate in samples[:100]]
bias = mean(stationary)
fit = samples[110:400]
holdout = samples[410:]


def rmse(rows, offset_ms, bias_rad_s):
    return sqrt(mean(
        (rate - bias_rad_s - reference(stamp - offset_ms / 1000)) ** 2
        for stamp, rate in rows
    ))


offset_ms = min(range(-80, 81), key=lambda ms: rmse(fit, ms, bias))
print(f"rest bias {bias:+.4f}, scatter {stdev(stationary):.4f} rad/s")
print(f"fitted offset {offset_ms:+d} ms")
for label, ms, correction in [
    ("raw", 0, 0), ("bias only", 0, bias), ("bias + time", offset_ms, bias)
]:
    print(f"{label}: holdout RMSE {rmse(holdout, ms, correction):.4f} rad/s")
```

预计偏差接近 +0.035 rad/s，分散接近 0.004 rad/s，正偏移接近 +40 ms。偏差校正使误差居中。定时校正应该使保持 RMSE 接近注入的散点。将记分器中的 `stamp - offset_ms / 1000` 更改为加法，同时牢记规定的约定。几乎相同的分数和负拟合值说明了为什么偏移需要记录的符号和时钟对，即使拟合非常好。

在录音中，使用独立标记的参考样本并在其有效范围内进行插值。绘制偏差校正残差与参考率斜率的关系图。一个小的后期标记以递增的速率使未校正的剩余负值。如果最佳偏移因时间窗口而异，请在增加拟合灵活性之前调查时钟漂移或缓冲。将拟合值、时钟配对、设备配置、校准数据标识符和保留指标放在一起。从模拟或记录的数据开始。任何硬件确认都属于监督调试程序。

## 练习：选择补充测量

模拟移动机器人在毫无特色的笔直走廊上不断迷失方向。它的IMU具有良好的短期重复性，平面激光雷达主要看到两个侧壁。墙壁可以帮助纠正哪些偏差？你将如何独立测试车轮秤？

<details>
<summary>检查你的推理</summary>
<p>墙壁方向可以限制偏航，并且它们的范围可以限制跨轨道位置。没有末端或地标的理想平行墙不提供沿走廊的位置提示。将带符号的编码器行程与独立测量的位移或仿真器真实情况进行比较，在两个方向和代表性牵引下进行多次直线穿越。将验证运行与拟合分开。</p>
</details>

## 练习：使偏移量无法识别

更改参考函数以返回常量 0.0。为什么实验室仍然可以估计偏差？你的校准工具应该报告什么有关偏移的信息？

<details>
<summary>检查结果</summary>
<p>平稳真值为零，因此观察到的平均值仍然估计偏差。每个偏移量都给出相同的参考值和损失。最小搜索返回其第一个并列候选者。该数据不提供时间信息。报告无法识别的偏移量并收集具有变化率的段。即使是单个周期性运动也可以产生多个以其周期分隔的合理偏移。</p>
</details>

## 弘扬什么

- 根据机器人的任务预算传感器误差，包括运行条件、样本寿命和覆盖范围。
- 保持内在、外在和时钟校准明确。验证独立观点或会议的偏差、分散性和可重复性。
- 校准的几何和时间戳支持[机器人感知](/zh/notes/robot-perception/)和[状态估计](/zh/notes/state-estimation/)。重新访问 [坐标系](/zh/notes/coordinate-frames/) 和 [针孔相机投影](/zh/notes/camera-projection/) 以进行变换和图像约定。
