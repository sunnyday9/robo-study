---
title: "机器人状态估计"
topic: "Perception and estimation"
order: "043"
description: "导出预测和更新、检查可观测性并重放卡尔曼滤波器，并进行缺失和虚假修复。"
prerequisites: "基本概率、矩阵乘法、Python 和传感器校准。"
minutes: 65
---

## 恢复传感器无法可靠检测到的数量

室内移动机器人在模拟中沿着笔直的通道行驶。轮编码器每次都会给出位移估计，即使远墙被遮挡也是如此。所测量的墙壁的偶尔范围提供了独立的位置固定，其中墙壁可见并且移动机器人面向它。车轮增量累积误差。墙壁修复有噪音、稀疏，有时会引用错误的表面。估计器应该同时使用两者并暴露其答案的不确定性。

通过必须推断的内容来定义你的状态。实验室需要固定参考系中沿过道的一个坐标 `x`（以米为单位）。对于在水平地板上自由移动的移动机器人，有用的姿态状态是 `(x, y, yaw)`，可能会随着速度或陀螺仪偏差而扩展。传感器测量值是该状态的函数。对于在坐标 `L` 处垂直于过道的测量墙壁，在实验室几何结构下，偏移 `d` 处的前向传感器的范围约为 `L - x - d`。将该范围转换为 `x` 一次，并将测量方差保留为 m²。错误的墙关联可以对错误的问题给出非常精确的答案。

## 贝叶斯过滤：传播，然后条件

<figure class="lesson-figure">
  <a href="/assets/figures/estimator-cycle.svg"><img src="/assets/figures/estimator-cycle.svg" width="640" height="420" loading="lazy" decoding="async" alt="车轮运动传播先前的估计。有效的墙壁测量可以纠正预测；丢失或拒绝的测量会使预测保持不变。"></a>
  <figcaption>即使墙壁修复缺失，预测也会运行。应用校正是一个单独的决定，取决于时间、几何形状和残差的大小。</figcaption>
</figure>

信念将概率分配给可能的状态。在每一步中，使用运动模型 `p(x_k | x_prev, u_k)` 将先前的信念扩展到新状态。这里 `u_k` 表示观察到的用作运动输入的车轮增量。当测量到达时，将预测置信度与其可能性 `p(z_k | x_k)` 相乘并进行归一化。因式分解假设所选状态包含运动模型所需的历史，并且测量有条件地独立于给定该状态和测量模型的早期数据。

```text
previous posterior -- motion input and process noise --> predicted belief
                                                              |
measurement at the same time --> compare with predicted value |
                                                              v
                            accepted measurement --> updated posterior
                            missing or gated out  --> keep prediction
```

在具有独立高斯噪声的线性模型中，卡尔曼滤波器传播均值和协方差，这充分描述了高斯信念。写入 `P` 作为状态误差的协方差。它的对角线保存方差，其非对角线条目捕获误差如何一起变化。例如，当移动机器人行进时，不确定的航向会导致横向位置不确定性增加。使用预测模型 `x = F x_prev + B u + w` 和测量模型 `z = H x + v`。 `Q` 和 `R` 是 `w` 和 `v` 的协方差。选择 `Q` 作为建模步骤和实际运行时间。编码器导出的姿态和速度可以共享车轮证据，因此天真地将两者视为独立更新可能会夸大信心。 [Welch 和 Bishop，卡尔曼滤波器简介](https://www.cs.cmu.edu/~motionplanning/papers/sbp_papers/kalman/welch_intro_kalman.pdf)

```text
Prediction: x_pred = F x_prev + B u        P_pred = F P_prev F^T + Q
Innovation: e = z - H x_pred              S = H P_pred H^T + R
Gain:       K = P_pred H^T S^-1
Update:     x = x_pred + K e
            P = (I - K H) P_pred (I - K H)^T + K R K^T
```

创新 `e` 是你在更新时可以观察到的差异。 `S` 是你对该差异期望的协方差。在 `H = 1` 的一维中，预测方差 `0.04 m²` 和测量方差 `0.01 m²` 给出 `K = 0.8`。提前 0.10 m 的定位会将估计值向前移动 0.08 m。更新后的方差为 `0.008 m²`。在矩阵代码中，使用线性求解增益。显示的协方差更新（称为约瑟夫形式）使其两个不确定性贡献变得明确。在标量情况下，它们简化为 `(1 - K) P_pred` 以获得此增益。

## 了解数据可以决定什么

可观察性询问是否可以通过随时间变化的输出来区分不同的候选状态。对于恒定线性模型，堆叠 `H`、`HF`、`HF²`，并进一步通电至比状态维度少 1。完整的列排名意味着在模型下的该窗口上可以观察到所有状态方向。对于平面移动机器人，仅车轮增量无法提供绝对起始位置的锚点。在笔直、均匀的走廊中，侧壁的范围不会限制沿这些墙壁的平移。相同几何形状的更多样本仍然会使该方向无法观察到。协方差沿着它缩小，需要对模型、先验和相关性进行审查。

对于非线性运动或测量，扩展卡尔曼滤波器 (EKF) 使用非线性函数来预测平均值和测量值。它在协方差计算中使用它们的局部导数或雅可比行列式。对于简单的前进步骤 `d`，增量 `d cos(yaw)` 和 `d sin(yaw)` 将航向误差与位置误差耦合。线性化是局部的。从合理的初始估计开始，将角度创新包装到一致的区间，并测试大的初始误差和转弯轨迹。粒子滤波器可以表示对称走廊中的多个位姿假设，但计算成本更高，并且需要在合理位姿附近保留足够的样本。 [Welch 和 Bishop，扩展卡尔曼滤波器](https://www.cs.cmu.edu/~motionplanning/papers/sbp_papers/kalman/welch_intro_kalman.pdf)

## 实验室：重放嘈杂的增量和稀疏的墙壁修复

另存为 `sensing-fusion.py` 并运行 `python sensing-fusion.py`。该夹具从已知位置开始，每 0.1 秒步进，并使用精确的模拟真实值在同一固定参考系中生成修复。修复中已经考虑了已知的墙壁几何形状。它会删除第 25 步至第 35 步中的预定修正，并在第 45 步中向修正添加 0.80 m。两个过滤器看到相同的数据。当创新平方除以创新方差超过 9 时，门会拒绝更新。对于正确建模的标量高斯创新，这是一个三标准差规则。该统计数据称为标准化创新平方（NIS），没有单位。

```python
from math import sqrt
from random import Random
from statistics import mean

rng = Random(43)
q, r = 0.035**2, 0.06**2  # process variance per tick, fix variance (m²)
rows = []
for k in range(1, 101):
    truth = k * 0.06
    wheel = 0.06 + rng.gauss(0, sqrt(q))
    fix = None
    if k % 5 == 0 and not 25 <= k <= 35:
        fix = truth + rng.gauss(0, sqrt(r)) + (0.80 if k == 45 else 0)
    rows.append((k, truth, wheel, fix))


def replay(gate):
    x = p = odom = 0.0
    errors, odom_errors, rejected = [], [], []
    for k, truth, wheel, fix in rows:
        odom += wheel
        x, p = x + wheel, p + q
        if fix is not None:
            innovation = fix - x
            s = p + r
            nis = innovation**2 / s
            if nis > gate:
                rejected.append(k)
            else:
                gain = p / s
                x += gain * innovation
                p *= 1 - gain
            if k == 45:
                print(f"step {k}: innovation={innovation:+.3f} m, NIS={nis:.1f}")
        if k in (20, 35):
            print(f"step {k}: posterior sigma={sqrt(p):.3f} m")
        errors.append((x - truth)**2)
        odom_errors.append((odom - truth)**2)
    print(f"RMSE fusion={sqrt(mean(errors)):.3f} m, "
          f"wheel={sqrt(mean(odom_errors)):.3f} m, rejected={rejected}")


for threshold in (float("inf"), 9.0):
    print(f"NIS gate={threshold}")
    replay(threshold)
```

在 dropout 过程中，不确定性应该会增加，并且门控过滤器应该跳过注入的修复。在比较轨迹 RMSE 之前检查步骤 45。在另一个种子上，合法的测量可能会超过阈值。针对预测的不确定性进行门控并跟踪拒绝运行。当创新规模很大时，请检查时间戳对齐、转换、噪声假设和数据关联。拒绝每一个修正可能会让估计器无限期地漂移。

在项目中，按采集顺序回放，通过传感器记录预门创新和 `S`，并与可用的独立事实进行比较。持续签署的创新表明存在偏见或滞后。转弯时的爆发表明几何形状、时间安排或缺少运动项。频繁进行重大创新的过滤器可能会低估不确定性。仅凭低 RMSE 无法建立校准的协方差。绘制保留轨迹的经验覆盖率和剩余一致性，包括丢失和延迟的数据。定义延迟观测是否被丢弃或通过有界历史与重新传播进行整合。对当前状态应用旧的修复会默默地改变观察模型。

## 练习：对车轮控制步误差建模

将车轮增量的平均值从 0.06 m 更改为 0.07 m。经过多次预测之后，修复的创新应该倾向于哪个方向？如何区分比例误差和墙坐标偏移？

<details>
<summary>检查你的诊断</summary>
<p>预测往往过于超前，因此修复往往会带来负面创新。在独立运行中，自可信修复以来，将位移误差与距离进行回归。比例误差随着带符号的行程而增大。恒定的墙坐标偏移会改变绝对定位。包括停止间隔、两个方向以及独立调查的参考文献。</p>
</details>

## 练习：根据位置修正估计速度

将实验室的运动模型替换为恒定速度和状态 `(x, v)`。使用时间步 `dt`，写入仅位置传感器的可观测性矩阵的前两行。一次即时修复会发生什么？

<details>
<summary>检查可观察性论证</summary>
<p>H 为 [1, 0]，HF 为 [1, dt]。他们的堆栈在非零 dt 中排名第二。随着时间的推移，位置测量携带有关速度的信息，尽管噪声和短间隔会影响其质量。一个瞬时位置定位会产生一个直接约束，并且无法单独确定这两个未知数。</p>
</details>

## 弘扬什么

- 使用运动模型来传播信念，并使用测量模型来调节信念。保持状态、协方差、框架和时间明确。
- 在添加状态变量之前检查可观察性。使用创新、覆盖范围和独立事实来调查估计者的行为。
- [地图和 SLAM](/zh/notes/mapping-and-slam/) 将这种推理扩展到重新访问位置并纠正全局参考系中的轨迹。
