---
title: "坐标系与坐标变换"
topic: "Kinematics"
order: "010"
description: "用两个坐标系表示同一个点，并按正确的方向串联坐标变换。"
prerequisites: "了解向量和基础三角函数。不需要机器人运行环境。"
minutes: 40
---

## 为什么会出现这个问题

假设相机报告“前方一米有个方块”。规划器还不能据此行动：这里的“前方”是相对于相机，还是相对于机器人基座？相机可能偏转，机器人也可能在图像到达之后移动。我们不必强迫每个组件都使用同一个坐标系，但必须在感知与规划的接口上定义可靠的转换。

调用库函数之前，先问三个问题：**原点在哪里？各坐标轴的正方向是什么？这个描述在哪一时刻有效？** 单独一个 `[1, 0, 0]` 无法回答这些问题。要让下游真正用得上位姿数据，就要同时说明坐标系、单位和时间戳。

最后，你应该能够在纸上预测变换，在 Python 中实现和测试它，并根据其症状识别逆变换。这里的几何形状是平面的，因此你可以看到失败的情况。接口规则也适用于三维[ROS 2 变换](/zh/notes/ros2-frames-and-time/)。

## 基本原理

当你在另一个坐标系中表达一个点时，它不会移动。只是它的坐标发生了变化。在本说明中，`T_A_B` 将坐标 **从 B 映射到 A**。它的旋转描述了 B 在 A 中的轴，它的平移描述了 B 在 A 中的原点。

```text
p_A = R_A_B · p_B + t_A_B
T_A_C = T_A_B · T_B_C
```

链接变换时，从右向左读取：C 中的点变为 B 中的点，然后 A 中的点。相邻的 B 下标匹配。始终使用列向量。

```text
point in C ── T_B_C ──▶ point in B ── T_A_B ──▶ point in A
        tool frame             wrist frame            base frame
```

旋转矩阵的每一列，都是用目标坐标系表示的一个源坐标轴。逆时针旋转 90° 时，源坐标系的 +X 对应目标坐标系的 +Y，源坐标系的 +Y 对应目标坐标系的 −X。这样就能直接写出矩阵的两列。平移向量描述源坐标系原点在目标坐标系中的位置，因此不能把这个向量再旋转一次。

在 3D 中，刚性变换通常封装为 4×4 齐次矩阵，其中 `R` 和 `t` 位于最后一行 `[0, 0, 0, 1]` 之上。点的最终坐标为 1；方向向量的最终坐标为 0。这就是为什么平移传感器会移动其原点，但不会改变其轴指向的方向。紧凑的矩阵形式，便于组合；它不是删除帧标签的许可证。

## 算例

传感器的原点位于基座坐标系中的 `(2, 1) m`。其轴相对底座逆时针旋转90°。它在自己的框架中看到 `(1, 0) m` 处的一个点。

1. 旋转点：`(1, 0) → (0, 1) m`。
2. 在基座坐标系中添加传感器原点：`(0, 1) + (2, 1) = (2, 2) m`。

要求逆变换，先减去平移向量，再乘以逆旋转矩阵。旋转矩阵的逆就是它的转置。

## 开发流程

从纯函数开始，而不是 ROS、矩阵包或相机。以下脚本使用与[浏览器实验](/zh/demos/#frame-lab) 中的绘图相同的约定。保存并使用Python 3运行它。返回值以米为单位；输入数学函数的角度以弧度为单位。

```python
from math import cos, isclose, radians, sin


def transform_point(point_source, origin_in_target, angle_deg):
    angle = radians(angle_deg)
    source_x, source_y = point_source
    offset_x, offset_y = origin_in_target
    return (
        cos(angle) * source_x - sin(angle) * source_y + offset_x,
        sin(angle) * source_x + cos(angle) * source_y + offset_y,
    )


def inverse_point(point_target, origin_in_target, angle_deg):
    relative = tuple(value - origin for value, origin in zip(point_target, origin_in_target))
    return transform_point(relative, (0.0, 0.0), -angle_deg)


def close(actual, expected):
    return all(isclose(left, right, abs_tol=1e-9) for left, right in zip(actual, expected))


origin = (2.0, 1.0)
assert close(transform_point((0.0, 0.0), origin, 90), origin)
assert close(transform_point((1.0, 0.0), origin, 90), (2.0, 2.0))
assert close(transform_point((0.0, 1.0), origin, 90), (1.0, 1.0))
assert close(inverse_point((2.0, 2.0), origin, 90), (1.0, 0.0))
print("OK: origin, both basis directions, and inverse")
```

为什么要进行这些检查？原点检测平移或操作顺序错误，而不依赖于旋转。两个基本方向暴露转置、交换轴和反射帧。逆过程检查两个边界是否组合回到同一点。单独的往返是很弱的：将两个实现交换为不正确但相互相反的约定仍然会通过它。

现在改变一个输入。将正向和反向调用更改为 -90°，并在更改预期值之前预测新的基础结果。在−90°时，+X 落在 `(2, 0)`，+Y 落在 `(3, 1)`。如果原点断言通过，但两个轴结果与预测相反，请检查角度符号或变换方向。如果所有三个位移量相同，请首先检查翻译和单位。

移植此代码时，请在连接真实传感器之前比较相同的四项检查。对于移动传感器，添加第二个固定装置：将其放置在两个不同的位姿上，并证明你在采集时选择了位姿。在错误时刻几何上正确的位姿可能会产生与校准误差相同的明显偏移。比较机器人静止和移动的运行情况以分离假设。

## 尝试一下

[在浏览器实验中转动传感器](/zh/demos/#frame-lab) 以查看其局部 x 轴在基本框架中的外观。

使用相同的传感器位姿，一个点位于基座坐标系中的 `(1, 1) m` 处。它的传感器坐标是多少？

<details>
<summary>检查你的答案</summary>
<p>减去传感器原点得到(−1, 0) m，然后顺时针旋转90°。结果是传感器坐标系中的 (0, 1) m。</p>
</details>

## 传输练习：读取转换链

手腕原点位于基础坐标中的 `(2, 1)` 处并旋转 +90°。工具原点位于沿手腕 +X 方向一米，其轴平行于手腕轴。基座坐标系中的工具原点是什么？为什么不能直接将 `(1, 0)` 添加到 `(2, 1)`？

<details>
<summary>检查链条</summary>
<p>在添加之前，将手腕框架偏移旋转到基座坐标系中的 (0, 1)。结果是 (2, 2)。添加原始偏移量会将两个分量向量视为以相同的基数表示。</p>
</details>

## 弘扬什么

- 名称按目标和源进行转换，并从数据开始写入链。
- 平移作用于一个点，但不作用于一个方向。逆运算会反转旋转和运算顺序。
- 分别验证原点、轴和时间。将原始坐标系 ID 和时间戳附加到观测结果中，以便下一个组件可以进行相同的检查。

## 阅读下一篇

- [现代机器人学§3.3.1：齐次变换矩阵](https://modernrobotics.northwestern.edu/nu-gm-book-resource/3-3-1-homogeneous-transformation-matrices/)
- [针孔摄像头投影](/zh/notes/camera-projection/)
