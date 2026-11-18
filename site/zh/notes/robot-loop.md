---
title: "写出第一个机器人闭环"
topic: "Robotics fundamentals"
order: "005"
description: "用 Python 搭建单轴小车模型，观察传感器偏差、延迟和执行器限幅如何改变闭环表现。"
prerequisites: "基础 Python，只用标准库。"
minutes: 45
---

## 从可测试的问题开始

让一辆仿真小车从原点出发，驶向 1 米外的目标。小车有速度上限。我们分别给测量值加上固定偏差和延迟，看看它如何响应。这一章不需要 ROS、物理引擎或神经网络：几行控制代码出了问题，就从逐项检查变量开始。

我们的验收测试很简单：经过 40 次迭代（每次迭代 0.1 秒）后，真实位置必须在目标的 0.08 m 范围内。这是该教学装置的标准，而不是机器人的物理要求。

## 在编码之前绘制系统

<figure class="lesson-figure">
  <a href="/assets/figures/closed-loop.svg"><img src="/assets/figures/closed-loop.svg" width="640" height="359" loading="lazy" decoding="async" alt="控制器读取位置、计算速度、施加限制并移动小车。小车改变的位置是在下一个控制步时测量的。"></a>
  <figcaption>从图中的 Observe（观测）开始顺时针看。先观测再发指令；小车移动后的位置信息留给下一步使用。</figcaption>
</figure>

**状态**是小车真实的位置；**观测**是控制器读到的位置，可能有延迟或偏差。**指令**是控制器期望的速度，**实际输入**则是限幅后真正施加给小车的速度。实际系统的各个环节都有不确定性，把这四个量分开记录，就更容易查到问题出在哪里。

每个控制步先通过传感器模型读取当前状态，接着计算指令，最后推进小车模型。不要在日志里把指令和执行后的状态配成一对：那不是控制器当时用来做决定的观测。这个顺序在[示范数据](/zh/notes/lerobot-data/)中也很重要。

## 构建第一个循环

将其保存为 `first_cart.py`，然后运行 `python first_cart.py`。它在每次调用时清空其状态，并且从不与硬件交互。该模型立即设置速度并忽略质量、摩擦和接触；后面的章节取代了这个假设，而不是给第一个实验增加无法解释的复杂性。

```python
def simulate(label, gain=2.0, bias=0.0, delay_ticks=0, speed_limit=0.5):
    target, time_step, ticks = 1.0, 0.1, 40
    positions = [0.0]
    peak = positions[0]
    clipped = 0
    for tick in range(ticks):
        observed_position = positions[max(0, tick - delay_ticks)] + bias
        error = target - observed_position
        requested_speed = gain * error
        applied_speed = max(-speed_limit, min(speed_limit, requested_speed))
        clipped += requested_speed != applied_speed
        next_position = positions[-1] + applied_speed * time_step
        peak = max(peak, next_position)
        positions.append(next_position)
        if tick in (0, 10, 20, 39):
            print(f"{label:8} t={tick * time_step:3.1f}s "
                  f"obs={observed_position:5.2f} "
                  f"request={requested_speed:5.2f} applied={applied_speed:5.2f}")
    final_error = abs(target - positions[-1])
    print(f"{label:8} final={positions[-1]:.3f} m, peak={peak:.3f} m, "
          f"clipped={clipped}, pass={final_error <= 0.08}")
    return final_error, peak


baseline_error, baseline_peak = simulate("baseline")
biased_error, _ = simulate("bias", bias=0.15)
_, delayed_peak = simulate("delay", delay_ticks=8)
assert baseline_error <= 0.08
assert biased_error > 0.08
assert delayed_peak > baseline_peak
```

在读取后面的值之前检查第一个控制步。控制器请求 2 m/s，设备可以应用 0.5 m/s，因此第一次移动为 0.05 m。位置误差与请求速度之间的比率以秒为单位。这些单元检查可以发现数量惊人的错误。

## 预测、运行和诊断

基线应该通过。偏置传感器告诉控制器小车比实际距离更远；即使测量误差为零，最终的真实位置也趋向于 0.85 m。调整增益无法消除信任​​该测量的控制器中的未知固定偏差。在调谐之前，将传感器读数与独立参考进行比较。

对于延迟运行，控制器作用于 0.8 秒之前的位置。当真正的小车到达目标后，它可以继续向目标移动。较大的峰值是症状；使用的最旧的测量值以及请求速度和应用速度之间的差异就是证据。不要仅使用最终错误来判断这种情况：它可能隐藏过度的偏移。

现在更改一个输入。将速度限制降低至 0.2 m/s，同时保持 4 s 水平线。即使完美的命令也无法克服 0.8 m 的距离限制。在提出另一个增益之前增加时间范围或更改设计约束。保持“目标不可行”和“控制器调整不当”之间的区别。

## 转移练习

你的迹线显示请求的速度为 +2 m/s，但位置在 0.1 s 的步长内仅改变 +0.05 m。积分器有错吗？

<details>
<summary>检查第一次推理</summary>
<p>不是根据这个证据。应用的速度限制为 +0.5 m/s，即 +0.05 m。在诊断集成之前记录应用的速度。</p>
</details>

队友更改脚本以记录每次移动后的最新位置作为该命令的输入。未来哪些实验会因此失效？

<details>
<summary>检查数据合同</summary>
<p>学习者或离线评估者可以使用该动作引起的信息来预测相同的动作。分别保存使用的实际观察、其采集控制步、命令以及结果的下一个状态。</p>
</details>

## 保留这个实验

保存脚本、基线输出、一个更改的条件以及对第一个错误假设的解释。你现在拥有一个完整的（尽管很小）机器人开发循环。接下来，在构建更真实的模型之前，[检查单位和时间戳](/zh/notes/robot-math-and-measurement/) 和[更改坐标系](/zh/notes/coordinate-frames/)。
