---
title: "运动轨迹与反馈控制"
topic: "Motion and control"
order: "033"
description: "为路径提供时间定律，通过扭矩前馈和反馈对其进行跟踪，并测量延迟和饱和的影响。"
prerequisites: "机器人动力学和驱动、PID 反馈以及基本导数。"
minutes: 60
---

## 一条路告诉你要去哪里

在两个固定装置之间移动零件的桌面臂需要路线和时间表。路径 `Q(s)` 按顺序指定配置，其中进度变量 `s` 从 0 到 1。时间规律 `s(t)` 指定手臂何时访问每个配置。它们一起形成轨迹 `q_ref(t) = Q(s(t))`。重用时间表较慢的路径会改变执行器的需求，同时保留几何配置的顺序。对标称路径的碰撞检查和对执行轨迹的测量回答了不同的问题。

要导出参考关节速度和加速度，请应用链式法则。素数是关于进度的导数，而点是关于以秒为单位的时间的导数。

```text
q_dot_ref  = Q'(s) s_dot
q_ddot_ref = Q''(s) s_dot² + Q'(s) s_ddot
```

将同一时间定律的持续时间加倍（归一化时间内），速度减半，加速度四分之一。平滑的计时仍然需要平滑的几何形状。非零速度路径中的急转弯需要速度的瞬时变化。在允许的区域内混合拐角或安排在那里停留。对于直线关节空间移动，请选择 `Q(s) = q_start + (q_end − q_start)s` 并尝试 `s = 10u³ − 15u⁴ + 6u⁵`，在持续时间 `T` 上使用 `u = t/T`。它以零速度和加速度到达两个端点。梯形速度曲线给出了恒定的加速度段和可能的巡航段，在过渡处具有加速度跳跃。检查整个运动（包括反转和制动）的峰值速度、加速度和所需扭矩。 [现代机器人学点对点时间定律](https://modernrobotics.northwestern.edu/nu-gm-book-resource/9-1-and-9-2-point-to-point-trajectories-part-2-of-2/)

## 预测扭矩并修正误差

对于[机器人动力学和驱动](/zh/notes/robot-dynamics-and-actuation/) 中的隔离关节，标称扭矩前馈为 `J_eq × q_ddot_ref + b × q_dot_ref`。这提供了模型预测加速和克服阻尼所需的内容。添加基于位置和速度误差的反馈，以对抗干扰和启动状态误差。在实验室中，这两种误差都使用参考值减去测量值。该比例微分 (PD) 定律使用测量的速度而不是位置误差的有限差分。如果应用需要抑制持续负载，积分项可以提供帮助，前提是稳定扭矩可行并且积分可以处理饱和。有关显式抗饱和实验，请参阅 [PID 反馈](/zh/notes/pid-feedback/)。 [现代机器人与扭矩输入运动控制](https://modernrobotics.northwestern.edu/nu-gm-book-resource/11-4-motion-control-with-torque-or-force-inputs-part-2-of-3/)

```text
path + clock -> reference position, velocity, acceleration
                   |                         |
                   v                         v
measured state -> error -> feedback -----> sum <- feedforward model
                   ^                         |
                   |                         v
                   +----- sample <--- joint <- torque limiter
```

将上面的路线读取为标称计算，将下面的回路读取为测量修正。控制器看到采样的状态，并且关节接收有限的总和。保存请求的扭矩和施加的扭矩。延迟可能来自传感、传输、过滤、计算或应用输出。记录样本的采集时间、计算时间和命令应用时间（如果有）。每 10 毫秒运行一次的控制器仍然可以使用 180 毫秒之前的测量值。如果有更多的延迟，则可以在错误改变符号后进行更正。提高增益可能会加剧由此产生的振荡。

## 如何选择控制器

状态空间描述了模型预测其未来所需的内容。该关节具有 `[q, speed]` 状态、控制输入扭矩以及可能仅测量的位置。观察者可以根据传感器历史和模型估计缺失状态。对于线性动力学，连续形式为 `x_dot = A x + B u`；在采样控制器中，当忽略干扰时，更新可以表示为 `x_next = A_d x + B_d u`。耦合模型可以解释影响多个测量输出的一个命令。这些是多种控制方法使用的建模选择。

| 方法 | 何时伸手去拿它 | 测量什么 |
| --- | --- | --- |
| PID | 在基本独立的轴和清晰的执行器接口上测量的误差。前馈可以减少它需要进行的修正。 | 稳定误差、过冲、噪声导数估计、饱和和饱和。 |
| 线性QR | 在工作点附近呈线性或有效的模型，具有可用或估计状态。调节器通过平衡二次状态错误惩罚与命令努力来选择状态反馈。跟踪通常使用标称轨迹和输入的偏差。 | 线性区域外的行为、估计的敏感性以及基本 LQR 中不存在的限制的影响。 [MIT的LQR笔记](https://underactuated.mit.edu/lqr.html) |
| 多点控制 | 预测模型和重要的显式约束，例如近期关节或扭矩限制。在未来范围内求解，应用第一个命令，然后从新的估计开始重复。 | 解决控制期限、不可行性处理以及模型预测跟踪和约束的效果等问题。 [MIT的MPC笔记](https://underactuated.mit.edu/trajopt.html#model-predictive-control) |

## 实验：保持模型和路径固定

保存为 `model-track.py` 并使用 Python 3 运行。模拟关节在 2 秒内从 0 弧度移动到 1 弧度，然后保持一秒钟。控制器中的模型知道惯性和阻尼。仅该设备就具有恒定的 0.06 N·m 反向扭矩。比较单独前馈、添加 PD、具有过时测量值的相同 PD，以及具有较小扭矩上限的相同 PD。在此实验中，10 ms 设备步骤和控制器周期一致。

```python
from math import sqrt

DT, MOVE, END = 0.01, 2.0, 3.0
INERTIA, DAMPING = 0.080, 0.12


def reference(time):
    u = min(1.0, max(0.0, time / MOVE))
    return (u**3 * (10 - 15*u + 6*u*u),
            30*u*u * (1-u)**2 / MOVE,
            60*u * (1-u) * (1-2*u) / MOVE**2)


def trial(name, feedback=False, delay=0, cap=0.60, load=0.06):
    history = [(0.0, 0.0)]
    squared_error = 0.0
    clipped = 0
    move_steps = round(MOVE / DT)
    for k in range(round(END / DT)):
        q, speed = history[k]
        goal, goal_speed, goal_accel = reference(k * DT)
        measured_q, measured_speed = history[max(0, k - delay)]
        requested = INERTIA * goal_accel + DAMPING * goal_speed
        if feedback:
            requested += 5.0 * (goal - measured_q)
            requested += 0.9 * (goal_speed - measured_speed)
        applied = min(cap, max(-cap, requested))
        clipped += applied != requested
        speed += DT * (applied - DAMPING * speed - load) / INERTIA
        history.append((q + DT * speed, speed))
        if k < move_steps:
            squared_error += (goal - q)**2
    rms = sqrt(squared_error / move_steps)
    final_error = 1.0 - history[-1][0]
    print(f"{name:13s} RMS={rms:.4f} rad  "
          f"final={final_error:+.4f} rad  clipped={clipped}")
    return rms, clipped


assert reference(0) == (0.0, 0.0, 0.0)
assert reference(MOVE) == (1.0, 0.0, 0.0)
nominal, _ = trial("nominal", load=0.0)
feedforward, _ = trial("feedforward")
tracked, _ = trial("with PD", feedback=True)
delayed, _ = trial("PD delayed", feedback=True, delay=18)
restricted, clips = trial("PD capped", feedback=True, cap=0.12)
assert nominal < tracked < feedforward
assert delayed > tracked and restricted > tracked and clips > 0
```

RMS 是移动过程中位置误差的均方根，最终误差将关节与 3 秒时保持的目标进行比较。标称试验检查无干扰的理想前馈计算。离散化仍然会产生少量残差。直接 PD 环路可减少负载下的误差并留下小的稳定偏移。在静止状态下，其比例项必须提供缺失的 0.06 N·m，因此预测的稳态误差为 `0.06/5 = 0.012 rad`。延迟反馈将当前参考与旧状态进行比较，这可以在手臂已经移动时产生较大的修正。如果上限较小，同一控制器会花费更多时间来请求模拟执行器无法提供的扭矩。

诊断较大的系统时，首先重放标称运行，然后单独扰动负载、时序和上限。在共享时间轴上绘制参考值、测量位置和速度以及请求与施加扭矩的关系。保留信号时间戳以诊断相位滞后。扫描延迟并跟踪 RMS、峰值误差和削波。对于对接或接触固定装置，还包括终端速度和间隙指标。通过自由关节模拟可验证对这些输入和假设的跟踪。物理接口需要自己的试运行检查和经过批准的限制的监督调试。

## 练习

1. 回放超出速度限制 1.4 倍，超出加速度限制 2.25 倍。对于相同的归一化时间定律，什么最小持续时间乘数可以解决这两个问题？接下来应该检查什么？

<details>
<summary>解决方案</summary>
<p>速度条件要求1.4以上，加速度要求2.25的平方根，即1.5以上。至少选择 1.5 并重新计算扭矩，包括负载和重力（如果存在）。这些条款可以保持低速。还要检查执行的跟踪和清除。</p>
</details>

2. 回放显示常规的 10 毫秒控制周期，但跟踪性能下降，并且请求的扭矩和施加的扭矩基本一致。你如何区分陈旧的反馈和刚度或负载的变化？

<details>
<summary>解决方案</summary>
<p>将获取时间与消耗状态的时间进行比较。首先使用新的测量值重放相同的对象、轨迹和控制器，然后使用测量的延迟重放。如果更改延迟会重现该症状，请检查延迟的来源。如果时机正确，请将卸载试验与受控负载变化进行比较，并检查位置和速度残差。</p>
</details>

## 总结

- 时间定律给出了几何路径速度和加速度。检查整个搬迁及其边界的可行性。
- 前馈提供名义努力。反馈可纠正执行器限幅和环路时序预算内的测量误差。
- 测试标称循环，然后一次更改一个假设。使用系统实际拥有的模型、信号、约束和期限来选择控制器。
