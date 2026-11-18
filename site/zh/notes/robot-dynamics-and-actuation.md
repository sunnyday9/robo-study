---
title: "机器人动力学与驱动"
topic: "Motion and control"
order: "031"
description: "将执行器命令和外部负载转化为预测的关节运动，然后测试哪些限制和力可以解释结果。"
prerequisites: "机器人运动学、基础代数和 Python。"
minutes: 55
---

## 从几何形状到负载下的运动

桌面臂可以使用空夹具或重负载到达同一点。 [运动学](/zh/notes/robot-kinematics/) 对于相同的关节角度给出相同的尖端位姿。负载的手臂可能加速更慢，需要更多扭矩，或者无法保持位姿。动力学将应用与加速联系起来。从围绕垂直轴旋转水平连杆的单个关节开始。重力对轴承施加负载，但在这种理想化情况下，它不会产生绕该轴的扭矩。

力的单位为牛顿 (N)。它关于原点的力矩是从原点到作用点的矢量与力的叉积。对于平面力，绕正 Z 轴的力矩为 `r_x F_y − r_y F_x`。在+Y 上施加2 N 的力在+X 上施加0.20 m 会产生+0.40 N·m。平行于杠杆的力贡献零力矩。因此，不同位置的相同力对于手臂来说可能容易或难以抵抗。

## 将扳手及其参考点放在一起

扳手将力和力矩封装在指定原点周围。假设你知道 `T_A_B`，其中旋转 `R` 和平移 `t` 在 A 坐标中从 A 原点到 B 原点。在 3D 中，关于 A 原点表达的同一扳手是

```text
F_A = R F_B
M_A = R M_B + t × F_A
```

力旋转，而力矩同时旋转并获得杠杆臂项。在 2 N 示例中，应用点处的传感器将报告那里的纯力力矩为零。移动到关节原点会产生 +0.40 N·m。计算功率时，力和速度必须使用兼容的框架和参考点。特别地，对于尖端力和尖端线速度，`F · (J q_dot) = (Jᵀ F) · q_dot`。因此，`Jᵀ F` 是该力贡献的关节扭矩矢量，即使位置雅可比行列式没有倒数。包括使用全扳手时的角速度和力矩。 [现代机器人扳手](https://modernrobotics.northwestern.edu/nu-gm-book-resource/3-4-wrenches/)

## 建立一个联合被控对象

被控对象是你要移动的系统。这里它的状态是以弧度为单位的关节角度 `q` 和以 rad/s 为单位的速度 `ω`。令 `J_eq` 为关节的有效惯量（单位为 kg·m²），`b` 为粘性阻尼（单位为 N·m/rad/s），`τ_load` 为带符号的负载参数，其正值表示负关节方向上的扭矩。如果关节反转，负载将保持其方向。粘性阻尼随速度改变符号。

```text
commanded motor     clip and multiply          sum torques
torque (N·m) -----> by gear ratio G ---------> (+ applied)
                                                (- b × speed)
                                                (- load)
                                                    |
                                                    v
                                         divide by joint inertia
                                                    |
                                                    v
                                       acceleration -> speed -> angle
                                                        |          |
                                         damping uses --+          +-- log
```

执行器增加扭矩。负载和阻尼输入相同的总和。在模拟中，加速度是净扭矩除以惯量，积分推进速度和角度。对方程求逆即可得出所需加速度和速度所需的施加关节扭矩 `J_eq × acceleration + b × ω + τ_load`。这就是正向动力学（加速度的输入）和逆向动力学（所需输入的期望加速度）之间的差异。对于多个关节，质量矩阵耦合加速度，运动相关项、重力和外部接触可能很重要。在介绍这些耦合之前，隔离轴是一个有用的测试用例。 [现代机器人学机械臂动力学](https://modernrobotics.northwestern.edu/nu-gm-book-resource/chapter-8-1-lagrangian-formulation-of-dynamics-part-1-of-2/)

将理想齿轮比定义为 `G = ω_motor / ω_joint`，符号对齐。 10:1 的减速比将电机扭矩乘以 10，并将其速度除以 10。理想变速箱中的功率保持不变。转子动能为 `0.5 J_motor (G ω)²`，因此转子对有效关节惯量的贡献为 `G² J_motor`。当连杆惯量为 0.050，转子惯量为 0.00030 kg·m² 时，10:1 结果为 0.080 kg·m²。对于给定的电机速度限制，增加可用关节扭矩的同一齿轮也会增加表观惯量并降低可用关节速度。比较传动装置时，请检查此转换的两个方向，并将所有负载和惯性保持在同一侧。 [现代机器人的传动和摩擦](https://modernrobotics.northwestern.edu/nu-gm-book-resource/8-9-actuation-gearing-and-friction/)

实际执行器可能具有取决于速度、电流或温度的扭矩限制。它们的接口可能接受扭矩、速度或位置，并由内部循环控制后两者。从接口和允许的操作范围开始。如果测量的残差需要，请添加摩擦细节。粘性扭矩与速度成正比。简单的库仑模型表示具有近似恒定相反大小的滑动摩擦。静摩擦可以使机构保持静止，同时平衡较小的施加扭矩。在零速度下具有零值的符号函数会忽略该行为，并且可能会在反转时产生数值抖动。

联系人有不同的签名。对于桌面推动器，一旦间隙闭合，通常会出现正常反应。基本干摩擦模型通过 `μ N` 限制切向力，其中 `N` 是压缩法向力。接触求解器可以确定与约束一致的反应，或者合规近似可以根据小渗透及其速率来计算它。使用刚性近似，减少积分步骤并在将接触尖峰视为物理之前检查峰值力和穿透力。下面的实验使用外加载荷，因此通过的结果仅验证自由接头方程。 [MuJoCo 接触锥和摩擦锥计算文档](https://mujoco.readthedocs.io/en/3.2.7/computation/index.html)

## 实验：将饱和度与阻尼分开

将代码保存为 `model-joint.py` 并使用 Python 3 运行 `python model-joint.py`。每次试验均保持所需的电机静止扭矩 0.09 N·m。电机的上限为 0.06 N·m，因此所有三个试验在接头处均收到 0.60 N·m。比较未加载的关节、具有相反扭矩的相同关节以及具有一半积分步长的加载关节。该玩具轴没有位置挡块。

```python
from math import exp, isclose

GEAR = 10.0
INERTIA = 0.050 + GEAR**2 * 0.00030
DAMPING = 0.12
MOTOR_LIMIT = 0.06


def simulate(load, dt):
    q = speed = 0.0
    request = 0.09
    applied = GEAR * min(MOTOR_LIMIT, max(-MOTOR_LIMIT, request))
    for _ in range(round(4.0 / dt)):
        acceleration = (applied - DAMPING * speed - load) / INERTIA
        speed += dt * acceleration
        q += dt * speed
    steady_speed = (applied - load) / DAMPING
    exact = steady_speed * (1 - exp(-DAMPING * 4.0 / INERTIA))
    print(f"load={load:.2f} N m, dt={dt:.3f} s, applied={applied:.2f} N m, "
          f"angle={q:.3f} rad, speed={speed:.4f} rad/s, steady={steady_speed:.2f}")
    assert isclose(speed, exact, abs_tol=0.002, rel_tol=0)
    return abs(speed - exact)


simulate(load=0.00, dt=0.010)
coarse_error = simulate(load=0.18, dt=0.010)
fine_error = simulate(load=0.18, dt=0.005)
assert fine_error < coarse_error
```

4 秒时，卸载速度应约为 4.99 rad/s，加载速度应约为 3.49 rad/s。在稳定速度下，加速度消失，阻尼平衡剩余扭矩，分别给出 5.00 和 3.50 rad/s。由于零速时的净扭矩较小，瞬态最初在负载运行中爬升得更慢。精确的速度来自时间常数为 `J_eq/b` 的一阶微分方程。将步长减半可减少​​相对于该参考值的数值误差。尽管速度变化平稳，但请求和施加的电机扭矩与第一个样本不同。

对于新模型，记录请求和应用的扭矩、速度、位置和时间戳。分别比较初始加速度和后期斜率。错误的初始斜率表明惯性、施加的扭矩或未建模的负载。验证扭矩下的错误终端速度表明存在阻尼或负载。差异集中在零速度附近表明粘滞、间隙或测量量化。在一条模拟或记录的轨迹上拟合参数，并在将拟合视为一般拟合之前检查不同的负载或反转。仅在其经批准的运动、扭矩和行程限制的监督下调试物理轴。

## 练习

1. 仿真关节必须在 0.18 N·m 的负载下承受 4 rad/s 的速度。改变控制器增益是否可以在给定的上限下实现这一点？

<details>
<summary>解决方案</summary>
<p>在稳定速度下，所需扭矩为 0.12 × 4 + 0.18 = 0.66 N·m。可用扭矩为0.60 N·m。增益变化无法提供缺失的稳定扭矩。该模型预测此负载的上限为 3.50 rad/s。</p>
</details>

2. 模拟力传感器沿底座 +X 为 0.20 m，其 +X 指向底座 +Y，其 +Z 沿底座 +Z。它报告沿传感器 +X 的 2 N 力，力矩为零。哪些基座坐标系下的力与力矩部件作用于接头原点？

<details>
<summary>解决方案</summary>
<p>将力旋转到基础坐标以获得 (0, 2, 0) N。使用 t × F 将力矩转移到基础原点，得到 (0, 0, 0.40) N·m。仅旋转报告的零力矩会错过关节上的负载。</p>
</details>

## 总结

- 添加绕公共轴和参考点的扭矩以预测加速度。对外部扳手的旋转和参考点进行建模。
- 齿轮装置以速度换取扭矩，并通过比率的平方反映转子惯量。阻尼、静摩擦和接触会产生不同的运动特征。
- 将模拟轨迹与分析案例进行比较，并在调整之前检查应用的限制。所需扭矩模型还为[轨迹跟踪](/zh/notes/trajectory-and-control/) 提供前馈。
