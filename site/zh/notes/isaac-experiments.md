---
title: "设计可重复的仿真实验"
topic: "Isaac Sim"
order: "084"
description: "控制步伐并捕捉节奏，然后将感知标签与动作演示分开，并根据各自的条件进行评估。"
prerequisites: "Franka 拾放基线和基本 Python 日志记录"
minutes: 50
---

## 决定你想从跑步中学到什么

弗兰卡演示曾捡起一个立方体。在收集一百集之前，问一个可以通过一批运行来回答的问题。例如，将立方体从标称生成点向侧面移动 2 厘米是否会降低使用同一控制器的固定放置成功率？名义生成时的重复可以告诉你基线是否足够稳定以解释变化。与单独的成功视频相比，带有相位跟踪的失败运行可以告诉你更多有关修复问题的信息。

对于本实验，目标是两个工件。首先，每个请求的运行的试验记录，包括失败和退出状态。其次，观察-行动契约，单独的读者可以围绕接触事件进行审核。这些回答了不同的问题：任务是否完成以及你是否捕获了学习者实际上可以使用的信息。即使实验暴露了错误，也保留两者。

## 决定每个控制步发生什么

物理时间步长控制解算器推进关节运动和接触的频率。控制期决定策略何时看到新的观察并选择行动。渲染计划控制何时绘制图像。传感器可以有自己的捕获节奏。 Isaac Sim 可以在每个渲染帧中推进几个物理步骤。对于实验，按仿真时间安排事件并按实际时间测量吞吐量。 [NVIDIA物理与渲染基础](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/physics/simulation_fundamentals.html)

![说明性仿真时间线，每个控制步有一个物理步骤，每两个控制步一次渲染，每四个控制步一个新的保持命令，每八个控制步一次相机采样。](/assets/isaac-cadence.svg)

在每秒模拟 120 个物理步骤时，每个控制间隔 4 个步骤每秒可做出 30 个决策。如果相机以 15 Hz 运行，则所有其他决策都需要重用最新的可用帧或遵循另一个明确选择的采样规则。重用的帧保留其捕获时间戳。将未来的映像加入到早期的操作会泄露策略在部署时永远无法看到的信息。

阅读控制步 4 或 33.3 毫秒处的图表。控制器对关节进行采样并在下一个物理间隔之前选择动作 1。到目前为止唯一的相机捕获是在控制步 0 处，因此如果图像已到达并且你的年龄预算允许 33.3 毫秒的陈旧时间，则操作 1 可以使用该图像。在控制步 8 处，新捕获和控制更新共享标称时间。仅当新映像在做出决定之前可用时才使用新映像。对于异步传感器，采集时间和可用性顺序都是需要的。如果勾选 8 图像在决策之后立即到达，则操作 2 可能会使用较旧的帧或将其记录为丢失。这些节奏说明了一种设计，与库存 Franka 测试的标称 60 Hz 物理步骤分开。

通过将一个动作保持四个物理步骤，你可以更改控制节奏，而无需粗化接触积分。它还为机器人提供了在下一次观察纠正偏差之前移动的时间。仅当帧到达时更新策略使得融合更容易推理，但将反馈与捕获率和抖动联系起来。在每次更快的控制更新时重用帧数据可以保持稳定的控制周期，同时需要明确的年龄限制和丢失图像行为。对于数据集，记录生成演示的策略。如果每个决策必须为下游读者提供唯一的图像，请相应地安排决策或设计显式关联，而不是克隆行和发明时间戳。

| 数据集 | 数据单位 | 它能回答什么 |
| --- | --- | --- |
| 综合感知数据 | RGB 或深度加上渲染标签，例如框或分段 | 模型能否在不同的光照下定位或分割立方体？ |
| 动作示范 | 具有情节边界的有序观察和命令对 | 学习者能否从现有观察中预测演示者的下一个命令？ |

Replicator 可以从渲染产品写入 RGB 和真实标签。运行 NVIDIA 的数据捕获：BasicWriter 示例并检查 `_out_basic_writer` 中的一张图像及其相应的框输出。下面的独立命令从安装目录运行。 [NVIDIA Replicator 示例](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/replicator_tutorials/tutorial_replicator_getting_started.html#data-capture-basicwriter)

```bash
./python.sh standalone_examples/api/isaacsim.replicator.examples/sdg_getting_started_01.py
```

检查该框是否包含预期的可见对象以及图像和注释文件名是否标识相同的捕获。这是来自渲染场景标签的监督。模仿样本具有不同的依赖性：在读取测量的状态和合格的图像后，专家计算命令并且仿真器应用它。块位姿可以用作特权专家输入或评估标签。如果部署的策略仅看到 RGB 和关节，请将该位姿排除在其输入特征之外。

## 实验室·重复运行并定义操作日志

1. 在新流程中运行两次包含 Franka 测试。保存日志和退出状态。 6.1.0 示例定义了测试模式下的步长预算，并检查立方体的提升和稳定是否在公差范围内。 Headless 删除应用程序窗口。 GPU 渲染仍然可以运行用于相机实验。 [已标记 Franka 测试源码](https://github.com/isaac-sim/IsaacSim/blob/v6.1.0/source/standalone_examples/api/isaacsim.robot_motion.examples/manipulation/pick_place.py) · [NVIDIA 无头性能笔记](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/reference_material/sim_performance_optimization_handbook.html)

   ```bash
   logs=$(mktemp -d) || exit 1
   printf 'Logs in %s\n' "$logs"
   for trial in 1 2; do
     if timeout --kill-after=15s 300s ./python.sh \
         standalone_examples/api/isaacsim.robot_motion.examples/manipulation/pick_place.py \
         --robot franka --headless --test > "$logs/$trial.log" 2>&1; then
       status=0
     else
       status=$?
     fi
     printf '%s\n' "$status" > "$logs/$trial.exit"
   done
   ```

   成功运行时预计状态为零和 `PASS: franka pick/place completed with a settled placement.`。 Bash 示例使用五分钟的墙预算。在运行批处理之前选择允许在主机上启动的预算。即使模拟步数计数器从未前进，墙壁超时也会捕获停滞的进程。

2. 在控制器生成命令的位置检测学习者拥有的示例副本。使用以下说明性伪代码来规划日志。记录实际发送到仿真机器人的动作，包括夹具命令。记下关节顺序、单位、动作模式和坐标系。

   ```text
   at each controller update:
       t = current simulation time
       obs = read measured joints and an eligible, already available frame
       action = expert command from this update
       submit action and record command time and applied values
       log episode ID, step index, t, observation, capture time and command
   at episode end:
       write termination reason and the measured placement outcome
   ```

   库存脚本没有相机捕捉。记录传递到 `controller.forward` 的测量状态以及通过 `scenario.apply_robot_state` 提交的目标。使用命名关节并记录命令模式和单位，包括棱柱手指的线性行程。对于相机，保留流 ID、帧、校准、编码和形状。同一模拟域中的时间戳状态和捕获。示例的 `controller_time` 每次控制器更新都会按标称时间步长前进，因此在使用它进行对齐之前请检查其与传感器标记的关系。重置时启动新的回合 ID，并保留源标记以及回合相对纳秒。

3. 比较相同场景、初始状态、仿真器和物理后端、驱动程序、时间设置和随机种子（如果适用）的重复运行。在比较跑步之前，根据你声明的容差检查步数、峰值提升、最终放置误差和结果。然后更改一个因素，例如立方体的起始位姿，然后重复。仅固定种子并不能保证跨设备和版本的按位相同的接触或图像。

检查站。验证每集内增加的决策时间、正确的动作维度和单位，以及决策时或之前的摄像机时间戳。如果捕获滞后于状态，请记录并检查样本年龄。如果关机时图像丢失，请排空写入器。 Replicator 为同步脚本提供 `rep.orchestrator.wait_until_complete()`。 [NVIDIA 捕获和写入生命周期](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/replicator_tutorials/tutorial_replicator_getting_started.html#wait-until-complete)

## 采集前测试观察合约

这个仅使用 Python 的示例对一集中的单个流进行建模。其事件序列记录帧传送和观察读取的顺序，而不从仿真时间中减去挂壁时间。

```text
Reader event       1               3              4               5
                  frame 0       decision       frame 1         decision
                  arrives       66.7 ms        arrives         100.0 ms
Capture stamp      0 ms                        66.7 ms
Selected frame                  missing                        frame 1
```

在事件 3 中，帧 0 超出了 40 毫秒的年龄限制，而帧 1 尚未到达。在事件 5 处，帧 1 可用，并且已存在约 33 毫秒。最后一个断言检查故意不一致的未来标记。

```python
def select_frame(frames, decision_ns, decision_seq, max_age_ns):
    eligible = (
        frame
        for frame in frames
        if frame["available_seq"] < decision_seq
        and 0 <= decision_ns - frame["capture_ns"] <= max_age_ns
    )
    return max(eligible, key=lambda frame: frame["capture_ns"], default=None)


frames = [
    {"id": 0, "capture_ns": 0, "available_seq": 1},
    {"id": 1, "capture_ns": 66_666_667, "available_seq": 4},
    {"id": 2, "capture_ns": 133_333_333, "available_seq": 6},
]
assert select_frame(frames, 66_666_667, 3, 40_000_000) is None
assert select_frame(frames, 100_000_000, 5, 40_000_000)["id"] == 1
# Deliberately inconsistent trace: a future-stamped frame is already queued.
assert select_frame(frames, 100_000_000, 7, 40_000_000)["id"] == 1
print("OK: frame availability and age gates")
```

预期输出是断言之后的打印行。仅将帧 1 的可用性从事件 4 更改为事件 2。预测第一个断言会失败，因为具有相同捕获时间的图像现在符合条件。用 ID 检查替换该断言以确认预期的选择，然后恢复原始装置。在真实的场景中，丢失的图像应该在跟踪中保持可见，以便你可以评估等待、后备或放弃决策的效果。 [capstone CPU 验证器](/zh/notes/capstone-tabletop/) 检查相关的 CSV 合约。它不检查图像传送顺序或内容。

## 运行配对比较并调试第一个分歧

烟雾运行后，制作一个标称和 +0.02 m 立方体 Y 偏移量的试验清单。从更改后的生成中导出拾取目标，以测试几何形状并通过正确指定的抓取来达到目标​​。保持地点区域、步骤预算、观察模式、物理设置和控制器固定。要包含初始状态的变化，请提前生成它们并在两种条件下使用相同的基础情况。重复启动固定场景探针在堆栈上的可重复性。

计算分母中所有预先声明的运行并按条件报告结果。例如，一个说明性的批次给出了 10/10 成功的标称试验和 7/10 的转移试验，其中有两次错过的提升和一次稳定超时。 30 个百分点的差异描述了这些试验。附近的一小部分位姿提供了关于更广泛工作空间的微弱证据。保留包含场景和资产修订、启动选项、启动状态、使用的种子、仿真器和驱动程序、相位跟踪、最大升力、最终 XY 误差、稳定结果和故障原因的清单。有限的控制器和挂机时间预算将缓慢的试验与挂起区分开来。参考成功检查适用于撤退后的对象，因此单独报告手臂完成情况。

比较第一个分歧阶段的通过和失败试验。假设转移的试验准确下降并可以举起木块，但有两个试验在释放之前将其掉落。在传输过程中测试手指接触和相对运动，而不是导出更多运行。如果在观察陈旧的地方丢弃集群，则重放附近的行并检查帧年龄以及状态、命令和物理的顺序。在慢动作期间，单排标签移位看起来似乎合理，并且当夹具关闭时变得明显。进行一次有针对性的更改，重新运行相同的试验列表，并保留早期的结果，以便有更改的证据。

## 将证据带入顶点

在桌面顶点中，回放录制的片段以验证读取器和数据合约。对于模仿研究，在拟合标准化之前按情节或场景组进行拆分，并保留单独的重置案例以进行首次评估。离线分数衡量记录观测结果的操作错误。当命令改变未来的观测结果时，闭环分数衡量任务的成功。如果两者都运行，则分别报告两者。与仿真相比，硬件还引入了校准误差、延迟、接触变化和执行器限幅。 [桌面顶石](/zh/notes/capstone-tabletop/)

本课程的 LeRobot 0.4.3 和 Python 3.12 实验室使用 PushT。 Franka 拾放具有不同的观察、执行器和执行语义。将演示和评估保留在各自的环境中，除非你实现并验证了架构、单元、框架和操作约定、控制时序和重置行为的显式适配器。仅兼容的文件布局无法将 PushT 位置命令转变为 Franka 联合目标。 [LeRobot 数据](/zh/notes/lerobot-data/) · [LeRobot 培训实验室](/zh/notes/lerobot-training/)

## 练习题及解答

为什么完美的离线动作得分可以与失败的闭环模拟抓握共存？

<details>
<summary>检查你的答案</summary>
<p>离线评分提供记录的观测结果。在首次展示中，操作会改变下一个观测结果。小错误或时间偏移可能会累积并驱动机器人进入演示未涵盖的状态。</p>
</details>

你将物理频率从 120 Hz 增加到 240 Hz，并保留旧除数 4 用于控制，8 用于相机。你打算单独研究接触集成。发生了什么变化？你将如何修复实验？

<details>
<summary>检查你的答案</summary>
<p>控制器现在以 60 Hz 运行，并且请求的相机调度为 30 Hz（假设渲染器容量）。最初是 30 和 15 Hz。使用 8 个物理控制步的间隔进行控制，使用 16 个物理控制步的间隔进行捕获，保持相同的模拟情节持续时间，并检查渲染和传输路径是否实际上以预期的节奏提供图像。然后比较配对试验。</p>
</details>

## 常见的误解

- 固定种子使运行具有可移植性和确定性。库版本、求解器后端、调度和硬件仍然会影响结果。保存配置并声明公差。
- 每一个渲染的图像都是一个演示。感知标签监督场景解释。模仿需要按时间顺序进行观察并从中发出命令。
- 更成功的回合将修复较低的推出分数。在生成可能包含相同错误的数据集之前，检查接触周围的操作对齐和失败。

## 总结

在一个仿真时钟上将物理、决策和捕获作为单独的时间表进行控制。将观测结果与它们可以通知的命令配对，用小型装置测试配对，并像记录成功一样仔细记录失败。匹配的试验列表可以使一项更改变得可解释。将生成的证据与生成它的任务和执行路径联系起来。
