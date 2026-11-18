---
title: "机器人运动学"
topic: "Motion and control"
order: "030"
description: "预测桌面手臂到达的位置，在逆解中进行选择，并检测它在哪里失去运动方向。"
prerequisites: "坐标系、三角学和 Python。偏导数很有帮助。"
minutes: 55
---

## 从目标到联合配置

桌面臂必须将标记笔尖带到一个点上。该点以距离底座的米为单位指定，而手臂则接受关节角度。运动学使用几何学将这些描述联系起来。它可以告诉你是否可以到达目标以及在给定的关节速度下尖端移动的速度。有关移动手臂所需的扭矩或标记在接触时如何表现的问题属于动力学。

从带有两个旋转关节的水平臂开始，称为 2R 臂。旋转关节绕轴旋转。肩部角度 `q1` 是从底座 +X 开始测量的，肘部角度 `q2` 是从第一个连杆的方向开始测量的。手臂有两个自由度 (DoF)，因为两个独立的坐标指定了其配置。计算数据结构中的坐标可能会给出错误的答案。例如，`(cos(q1), sin(q1))` 存储两个具有一个约束的数字，因此它代表一个自由度。 [现代机器人自由度](https://modernrobotics.northwestern.edu/nu-gm-book-resource/2-2-degrees-of-freedom-of-a-robot/)

配置空间包含可能的联合配置。对于不受限制的角度，它会环绕每个轴上的每个整圈。对于物理关节限位，在比较角度或检查移动时使用实际允许的间隔。任务空间描述了作业要求你控制的内容，此处提示为基本框架中的 `(x, y)`。此任务的工作空间是该平面的可到达子集。完全旋转且没有障碍物时，它是一个内半径为 `abs(L1 - L2)`、外半径为 `L1 + L2` 的圆环。实际的停止和障碍物进一步限制了手臂可以操作的位置。更改任务以包括标记方向会添加第三个请求的组件，该两关节臂无法独立指定该组件。 [现代机器人的任务空间和工作空间](https://modernrobotics.northwestern.edu/nu-gm-book-resource/2-5-task-space-and-workspace/)

## 从已知帧构建位姿

<figure class="lesson-figure">
  <a href="/assets/figures/two-ik-solutions.svg"><img src="/assets/figures/two-ik-solutions.svg" width="640" height="353" loading="lazy" decoding="async" alt="两种手臂配置共享一个底座和一个尖端目标。实线路径的弯头位于 X 轴上方，虚线路径的弯头位于 X 轴下方。"></a>
  <figcaption>两种联合解决方案都达到了相同点。使用起始位姿、关节限制和障碍物（而不是仅使用尖端位置）来选择分支。</figcaption>
</figure>

使用[坐标系](/zh/notes/coordinate-frames/) 中的约定。 `T_A_B` 将坐标从 B 转换为 A。平面刚性姿态属于 SE(2)，可以存储为 3×3 齐次矩阵，具有 2×2 旋转 `R`、二分量平移 `t` 和最后一行 `[0, 0, 1]`。 SE(3) 是具有 3×3 适当旋转、三分量平移和最后一行 `[0, 0, 0, 1]` 的空间模拟。旋转列是行列式+1 的单位垂直轴。在这两种情况下，变换均构成刚性运动，其逆变换具有旋转 `Rᵀ` 和平移 `−Rᵀt`。 [齐次变换的现代机器人](https://modernrobotics.northwestern.edu/nu-gm-book-resource/3-3-1-homogeneous-transformation-matrices/)

对于手臂，从肩架开始并旋转 `q1`。下一个原点是沿转肩 +X 的 `L1`。在那里旋转 `q2`，然后将 `L2` 沿着转动的肘部的 +X 移动到尖端。按所写顺序乘以变换以获得 `T_base_tip`。将其应用到尖端原点以获得 `p_base`。要求解已校准任务框架中提供的目标，请首先将 `T_base_task` 应用于该目标。对于移动框架，在相关观察时间使用变换和联合状态。

```text
View from above, +Y up and +X right (sketch is not to scale)

              elbow B
             /       \
         L1 /         \ L2
           /           \
 shoulder +             * shared target (x, y)
           \           /
         L1 \         / L2
             \       /
              elbow A
```

两种弯曲配置从肩部到目标线的不同侧到达相同的尖端点。它们的尖端方向通常不同。对于任一配置，正向运动学 (FK) 在基本坐标中添加两个连杆位移：

```text
x = L1 cos(q1) + L2 cos(q1 + q2)
y = L1 sin(q1) + L2 sin(q1 + q2)
tip heading = q1 + q2   (modulo a full turn)
```

## 求解两个肘部并选择一个分支

逆运动学 (IK) 从所需的任务值开始。在距离肩部 `d` 处，余弦定律给出 `d² = L1² + L2² + 2 L1 L2 cos(q2)`。求解 `c = cos(q2)`。 `[-1, 1]` 之外的值超出数值公差意味着几何模型无法达到目标。在内部，`sin(q2)` 可以是任一标志。使用 `atan2(sin(q2), c)` 恢复带符号的角度。肩部航向是轴承 `atan2(y, x)` 减去转动肩部框架中尖端的轴承 `atan2(L2 sin(q2), L1 + L2 cos(q2))`。在环面边界处，分支以整圈为模重合。折叠到其自身底座上的等长臂是具有无限多个肩角的特殊情况。我们不平等的长度避免了这种歧义。 [现代机器人开链逆运动学](https://modernrobotics.northwestern.edu/nu-gm-book-resource/inverse-kinematics-of-open-chains/)

对于一系列目标，保留两个候选目标，直到检查关节限制和碰撞并比较当前配置的允许运动。最近的端点仍可能需要有阻碍的方法。还要检查扫掠运动。对于更复杂的手臂，数值求解器可以迭代地减少初始猜测的尖端误差。从当前配置中播种以确保连续性，检查最终残差，并在必要时尝试其他种子。仅失败的迭代并不能证明几何上不可能。 [现代机器人学数值IK](https://modernrobotics.northwestern.edu/nu-gm-book-resource/6-2-numerical-inverse-kinematics-part-1-of-2/)

## 读取速度并检测奇点

雅可比 `J(q)` 位置的每个关节有一列。列 `i` 区分相对于关节 `i` 的两个 FK 坐标，同时保持另一个固定。根据链式法则，`p_dot = J(q) q_dot`。将列（米/弧度）乘以关节速率（弧度/秒）可得出以米/秒为单位的基座坐标系速度。

对于此任务，`det(J) = L1 L2 sin(q2)`。当伸直或完全折叠时，两个列方向共线。即使接头仍在转动，尖端也会失去瞬时径向运动。接近该奇点时，控制径向末端速度可能需要过高的接头速率。阻尼最小二乘逆函数将任务误差换成更小的速率。如果你需要在丢失方向上进行精确运动，请计划不同的方法并评估残余速度和关节速度。 [现代机器人奇点](https://modernrobotics.northwestern.edu/nu-gm-book-resource/5-3-singularities/)

## 实验：证明你的 FK、IK 和雅可比行列式一致

使用没有依赖项的 Python 3。将块保存为 `model-arm.py` 并运行 `python model-arm.py`。选择 0.30 m 和 0.20 m 链接并首先在纸上预测零回转和四分之一回转位姿。然后找到同一点的两个根，并将每个解析雅可比列与中心有限差分进行比较。

```python
from math import atan2, cos, dist, pi, sin, sqrt

L1, L2 = 0.30, 0.20


def fk(q1, q2):
    return (L1*cos(q1) + L2*cos(q1 + q2),
            L1*sin(q1) + L2*sin(q1 + q2))


def ik(x, y):
    c = (x*x + y*y - L1*L1 - L2*L2) / (2*L1*L2)
    tolerance = 1e-12
    if abs(c) > 1 + tolerance:
        return []
    if abs(abs(c) - 1) <= tolerance:
        c = 1.0 if c > 0 else -1.0
    s = sqrt(1 - c*c)
    return [(atan2(y, x) - atan2(L2*signed_s, L1 + L2*c),
             atan2(signed_s, c))
            for signed_s in ((s, -s) if s else (0.0,))]


def jacobian_columns(q1, q2):
    x, y = fk(q1, q2)
    return (-y, x), (-L2*sin(q1 + q2), L2*cos(q1 + q2))


assert dist(fk(0, 0), (0.50, 0)) < 1e-12
assert dist(fk(pi / 2, 0), (0, 0.50)) < 1e-12
assert len(ik(0.50, 0)) == len(ik(0.10, 0)) == 1
assert ik(0.51, 0) == ik(0.05, 0) == []
roots = ik(0.30, 0.20)
assert len(roots) == 2 and roots[0][1] > 0 > roots[1][1]
step = 1e-6  # rad
for q1, q2 in roots:
    assert dist(fk(q1, q2), (0.30, 0.20)) < 1e-12
    pairs = [(fk(q1 + step, q2), fk(q1 - step, q2)),
             (fk(q1, q2 + step), fk(q1, q2 - step))]
    for column, (plus, minus) in zip(jacobian_columns(q1, q2), pairs):
        numeric = tuple((a - b)/(2*step) for a, b in zip(plus, minus))
        assert dist(column, numeric) < 1e-8
    print(f"q = ({q1:.3f}, {q2:.3f}) rad, tip checks pass")

for angle in (pi / 2, 0.01, 0.0):
    (a, b), (c, d) = jacobian_columns(0, angle)
    print(f"q2={angle:.3f} rad, det(J)={a*d - b*c:.6f}")
```

预计根接近 `(0.000, 1.571)` 和 `(1.176, −1.571)` rad。行列式从 0.060000 下降到大约 0.000600 到零。通过首先将目标转换为基数，重复非零基数到任务的转换。如果夹具位姿失败，请在触摸 IK 之前检查链接单位和角度零点。如果分析列和数值列不一致，请检查扰动改变的角度以及导数输出是否位于基本框架中。这些检查在 Python 中建立了一致性和简单的几何案例。用于调试的手臂模型还需要独立检查链接尺寸、框架偏移、关节限制以及模拟或监督试运行验证。

## 练习

1. 在 `(0.30, 0.20) m` 处，模拟关节限位仅允许 `−2.0 ≤ q2 ≤ 0.2` rad。还剩下哪位候选解以及还缺少哪些检查项？

<details>
<summary>解决方案</summary>
<p>第二个解大约为 (1.176, -1.571) rad，超过了弯头极限。在接受之前检查肩部限制、模型的碰撞以及当前关节状态的扫掠运动。</p>
</details>

2. 在 `q = (0, 0)` 处，预测关节速率 `(0.4, −1.0) rad/s` 的末端速度。这对于以该位姿沿 +X 进行笛卡尔点动意味着什么？

<details>
<summary>解决方案</summary>
<p>列为 (0, 0.50) 和 (0, 0.20) m/rad，因此这两个贡献相互抵消，末端速度为 (0, 0) m/s。更一般地，在此位姿下，每个可达到的瞬时末端速度的 x 分量为零。沿 +X 移动也会超出工作空间边界。在请求径向运动之前重新定位远离边界。</p>
</details>

## 总结

- 联合配置指定了机制。所选任务及其工作区描述了可以在提示处命令的内容。
- FK 组成已知变换。 IK 可以返回多个关节状态，每个关节状态都需要可行性和路径检查。
- 雅可比行列式将关节速率映射到末端速度。无论 FK 是否正确，排名的损失都会删除瞬时方向。要询问什么输入使手臂移动，请继续[机器人动力学和驱动](/zh/notes/robot-dynamics-and-actuation/)。
