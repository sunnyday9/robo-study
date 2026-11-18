---
title: "移动机器人的运动模型"
topic: "Motion and control"
order: "034"
description: "将差动驱动轮运动转换为位姿估计，并诊断滚动假设不成立的地方。"
prerequisites: "坐标系、基本三角学和 Python。"
minutes: 55
---

## 从轮子允许的运动开始

室内移动机器人有两个位于公共轴上的驱动轮和一个被动支撑脚轮。轮子可以使其向前滚动、原地转动或划出弧线。要将一个车身宽度停放在左侧，它必须改变航向并通过机动进行滚动。它不能直接向左平移，同时保持两个轮子滚动而不会侧滑。平面位姿具有三个坐标 `(x, y, θ)`，而该基座具有两个独立的瞬时输入。该速度约束称为非完整约束。如果有机动空间，差动驱动器仍然可以达到向其侧面偏移的姿态。 [ros2_control谈轮式机器人运动学](https://control.ros.org/jazzy/doc/ros2_controllers/doc/mobile_robot_kinematics.html)

## 在车轮和车身速度之间转换

使用轴中点作为移动机器人运动主体框架的原点。选择+X 向前、+Y 向左和+Z 向上。从上方看，正偏航为逆时针旋转。该位姿给出了固定里程框架中的轴中点和偏航，最初与机器人对齐。采用米、秒、弧度和车轮旋转标志，当火星车向前滚动时，两个车轮都报告正值。该符号约定是在考虑了编码器的安装方式后定义的。 [坐标系](/zh/notes/coordinate-frames/) · [ROS REP 103](https://github.com/ros-infrastructure/rep/blob/master/rep-0103.rst)

```text
Top view
                      +X forward
                           ^
                           |
  left contact L ----------o---------- R right contact
                 <---------+           o = axle midpoint
                  +Y left
  |<------- track width W (m) ------->|

  For a forward left arc: right wheel travels farther than left.
```

将轮距称为 `W`，滚动半径为 `r_L, r_R`，带符号的车轮角速率为 `Ω_L, Ω_R`。无滑移滚动将每个角速率映射到车轮的纵向速度 `v_i = r_i Ω_i`。左侧触点位于 `y = +W/2` 主体，右侧触点位于 `y = −W/2`。围绕 +Z 的旋转减去左侧接触处的前进速度并在右侧加上它，给出反向和前进映射：

```text
v_L = v − ω W/2                 v   = (v_R + v_L)/2
v_R = v + ω W/2                 ω   = (v_R − v_L)/W
Ω_i = v_i / r_i                  v_y = 0 at the axle midpoint
```

这里 `v` 是车身前进速度，单位为 m/s，`ω` 是偏航角速度，单位为 rad/s。相同的轮速产生直线运动。相同和相反的速度可实现原地转弯。在具有 0.30 m 轨道的 `v = −0.20 m/s` 和 `ω = +1 rad/s` 处，两个地面速度为 `−0.35` 和 `−0.05 m/s`。移动机器人反转，同时偏航仍然增加。如果在保留 `ω` 的同时反转 `v`，则有符号路径曲率 `ω/v` 会改变符号；检查上游规划器是否通过曲率或偏航率定义反向弧。如果两个轮子命令都必须符合速度限制，则按相同的正因子缩放两者会保留圆弧几何形状并减慢进度。单独修剪一个车轮通常会改变曲率。

## 集成有符号编码器行程

轮编码器测量旋转。对于车轮每转一圈计数为 `N` 的计数器，连续计数 `n_old` 和 `n_new` 意味着滚动模型下的带符号行程 `d = 2πr (n_new − n_old)/N`。如果编码器位于电机轴上，请首先将记录的计数和传动装置转换为车轮转数。在确定一个计数的含义时，包括任何解码器乘法。在一致的时间进行配对轮测量，在求差之前展开有限计数器，并将重置处理为显式不连续性。将行程除以测量的时间间隔即可估算平均速度。旅行本身已经跨越了该间隔，因此不要再次乘以时间。

使用 `Δs = (d_R + d_L)/2` 和 `Δθ = (d_R − d_L)/W`，将轴中点集成到里程计坐标中。如果车轮速率在整个区间内保持恒定，则中点将绘制圆弧或直线。其和弦的签名长度为 `Δs sinc(Δθ/2)`，标题为 `θ + Δθ/2`，其中包含 `sinc(a) = sin(a)/a` 和 `sinc(0) = 1`。将该弦投影到里程计 X 和 Y 上，然后将 `Δθ` 添加到偏航。这给出了精确的恒定速率更新。在起始航向处采取一步是更简单的欧拉积分，并且可能会引入转弯误差。对于更改车轮速率，请使用较短的时间对齐间隔，因为仅行程总计就会丢失有关转弯和平移顺序的信息。

## 实验：重放合成编码器对

将代码保存为 `model-odometry.py` 并使用 Python 3 运行 `python model-odometry.py`。每次运行都从原点开始，代表一秒的恒定轮速，每 0.05 秒采样一次。仿真器将绝对编码器计数量化为车轮每转 2048 个计数。在一次试验中，右轮旋转的速度超过了其在地板上的有效前进速度。根据规定的地面行程计算出的独立姿态代表仿真器真值情况。这些是具有简化滑动场景的合成痕迹。

```python
from math import cos, dist, pi, sin

WIDTH = 0.30
METERS_PER_COUNT = 2 * pi * 0.05 / 2048
ORIGIN = (0.0, 0.0, 0.0)
SAMPLES = 20


def advance(pose, left, right):
    x, y, yaw = pose
    turn = (right - left) / WIDTH
    half_turn = turn / 2
    sinc = sin(half_turn) / half_turn if half_turn else 1.0
    chord = (left + right) / 2 * sinc
    heading = yaw + half_turn
    return x + chord*cos(heading), y + chord*sin(heading), yaw + turn


def replay(left, right):
    pose = ORIGIN
    last_left = last_right = 0
    for sample in range(1, SAMPLES + 1):
        fraction = sample / SAMPLES
        left_count = round(left * fraction / METERS_PER_COUNT)
        right_count = round(right * fraction / METERS_PER_COUNT)
        pose = advance(pose, (left_count - last_left) * METERS_PER_COUNT,
                       (right_count - last_right) * METERS_PER_COUNT)
        last_left, last_right = left_count, right_count
    return pose


fixtures = [
    ("forward", 0.30, 0.30, (0.30, 0.0, 0.0)),
    ("reverse", -0.30, -0.30, (-0.30, 0.0, 0.0)),
    ("spin", -0.15, 0.15, (0.0, 0.0, 1.0)),
    ("arc", 0.15, 0.45, (0.30*sin(1), 0.30*(1 - cos(1)), 1.0)),
]
for name, left, right, expected in fixtures:
    x, y, yaw = replay(left, right)
    assert dist((x, y), expected[:2]) < 0.002
    assert abs(yaw - expected[2]) < 0.002
    print(f"{name:7s} x={x:+.3f} m, y={y:+.3f} m, yaw={yaw:+.3f} rad")

estimate = replay(0.30, 0.30)
truth = advance(ORIGIN, 0.30, 0.24)
print(f"slip: position error={dist(estimate[:2], truth[:2]):.3f} m, "
      f"yaw error={estimate[2] - truth[2]:+.3f} rad")
```

预计 X 上的正向运行接近 +0.300 m，反向运行接近 -0.300 m，旋转接近 +1.000 rad，没有平移。电弧应在 `(0.252, 0.138) m` 附近结束。在滑移试验中，相等的计数预测直线运动，而规定的有效地面行程预测 -0.200 rad 的偏航。仅更改编码器分辨率无法解决具有相同编码器读数的两个物理结果。

在依赖里程计之前，使用直线、旋转和弧线回放进行调试。两个方向上一致的距离控制步误差建议检查每转或车轮半径的计数。经验证的直线行驶期间的曲线估计表明左/右比例不匹配或迹象。旋转期间可重复的偏航增益误差表明在检查两个半径控制步后轨道宽度不匹配。使用改变的速度和模拟表面抓地力运行相同的场景，以区分持续的校准误差和滑动。与独立时间戳的姿态或航向进行比较，并分别报告位置和偏航。在 ROS 词汇中，`odom` 是连续的，但可能会漂移，而全局定位估计可以纠正长期位置。 Jazzy 的 `diff_drive_controller` 可以根据关节反馈计算里程计，或者在配置为开环时使用命令。这里的示例是合成编码器的独立重放。 [ROS REP 105](https://github.com/ros-infrastructure/rep/blob/master/rep-0105.rst) · [Jazzy 差动驱动控制器文档](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html)

## 比较替代机箱

对于阿克曼底盘，内前轮和外前轮以不同角度转向，以遵循理想模型中的同心圆。通过自行车模型中的单个虚拟前轮来近似它们。对于后轴速度 `v`、轴距 `L` 和虚拟转向角 `δ`，横摆率为 `(v/L) tan(δ)`。传统的转向范围给出了最小转弯半径并且没有原地旋转。相同转向角的倒车速度会逆转横摆角速度。具有适当布置的全向轮的全向底盘可以以其理想的运动学独立地控制向前、横向和偏航速度。它可以避开扩展坞。车轮牵引力、滚轮接触和电机限制仍然决定着它所达到的效果。根据平台和对接几何形状选择模型，然后通过模拟回放和监督调试（如果适用）进行验证。 [全向轮、自行车模型和阿克曼转向上的 ros2_control](https://control.ros.org/jazzy/doc/ros2_controllers/doc/mobile_robot_kinematics.html)

## 练习

1. 模拟移动机器人请求 `v = 0.30 m/s` 和 `ω = 2.0 rad/s` 以及 `W = 0.30 m`。每个轮子的大小限制为 `0.45 m/s`。找到在保持转弯半径的情况下可达到的车轮速度。

<details>
<summary>解决方案</summary>
<p>反演图给出左 0.00 和右 0.60 m/s。将两者乘以 0.75 即可得到 0.00 和 0.45 m/s。主体现在以 0.225 m/s 的速度移动，以 1.50 rad/s 的速度转动，保持 0.15 m 的转动半径。</p>
</details>

2. 两个合成回放报告相同的编码器计数。仿真器真实通道显示高抓地力表面上的相等距离​​和低抓地力表面上意外的向右偏航。在更改车轮半径之前应该比较哪些测量值？

<details>
<summary>解决方案</summary>
<p>通过采集时间对齐车轮计数、独立测量的偏航和车身路径，并以多种速度检查相同的移动。半径误差也会持续影响高抓地力运行。抓地力或加速后的残差表明打滑。诊断时保持标称校准固定，因为仅编码器旋转无法区分两条迹线。</p>
</details>

## 总结

- 差速驱动图作用于车轴中点。前进速度是车轮平均速度，带符号的横摆角速度来自差值除以轮距宽度。
- 将带时间戳的车轮沿着车身弧线的行程积分，并将该位移旋转到里程计坐标中。
- 将里程计与独立参考进行比较。选择与机动相匹配的底盘模型，并评估其滚动假设失败的地方。
