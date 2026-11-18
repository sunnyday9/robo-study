---
title: "评估模仿学习策略"
topic: "LeRobot"
order: "094"
description: "验证数据契约并测量可重现仿真器重置的闭环行为。"
prerequisites: "ACT 检查点和 PushT 环境"
minutes: 45
---

## 让失败变得可解释

假设两个策略都超时。一个人永远不会接触到T。另一个人将其推向球门附近，然后将其发送到侧面。成功率对这两种结果一视同仁。这些视频提出了不同的后续实验，并且没有告诉你处理器是否交换了动作坐标。你的目标是其他开发人员可以重现和调试的评估。生成固定重置的结果表、与更改的推理设置的匹配比较，以及解释第一个相应差异的跟踪或视频。

## 验证策略-环境契约

在运行学习的策略之前，请验证已知的观测结果和已知的操作。当 x 和 y 交换或绝对目标被解释为增量时，形状检查可以通过。在独立诊断部署中，选择代理远离 T 的重置，并命令其当前 x 加 20，y 保持不变。检查步骤前后的数字位置并将方向与图像匹配。如果适配器剪辑了请求的目标和应用的目标，则分别记录它们。即使所调度的命令是有限的，超出范围的预测也是有关策略或其转换的证据。本实验使用 LeRobot 的内置 PushT 集成。 [已标记 PushT 配置](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/envs/configs.py) · [PushT 观察和操作空间](https://pypi.org/project/gym-pusht/0.1.6/)

| 边界 | 检查这个检查点 |
| --- | --- |
| 仿真器→观察 | `pixels` 变为 `observation.image`，RGB 输入为 96 × 96。在策略标准化之前确认通道顺序并缩放到 `[0, 1]`。 `agent_pos` 按 x、y 顺序变为 `observation.state`。 |
| 策略→仿真器 | 保存的后处理器返回仿真器单位中的绝对 x, y 目标。仿真器的可接受范围是每轴 `[0, 512]`。使用已知的水平目标检查边界、单位和方向，并对超出范围的预测进行计数。 |
| 计时和重置 | 仿真时间每 0.1 秒发出一个命令。 ACT 检查点在重新计算之前消耗四个排队的操作。每次环境重置时都会重置策略队列。 |

```text
Reset(seed) clears physics state and the policy queue
   |
   v
o[t] --> image/state mapping --> saved preprocessor --> ACT queue
 ^                                                      |
 |                                                      v
o[t+1] <-- simulator step <-------------------- saved postprocessor
                |
                +--> reward, termination, truncation, success
```

读取从 `o[t]` 到命令的循环，然后到 `o[t+1]`。只有仿真器步骤会提前仿真时间。如果你需要区分重用目标和新预测，请记录重新计划标记和已发出的操作。标记的评估器会重置策略并在单步执行之前应用策略和环境处理。 `observation_height` 和 `observation_width` 设置在 LeRobot 的配置中声明 96 × 96 功能。在此版本中，LeRobot 转发的 PushT 构造函数参数中不存在这些字段，并且固定的gym包本身默认为 96 × 96 观察值。视频渲染大小是一个单独的设置。如果移植实验室，请检查实际的输入张量。 [标记评估推出](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/scripts/lerobot_eval.py)

## 实验室·评估两组重置用的随机种子

从 [training lab](/zh/notes/lerobot-training/) 目录运行此 Bash 循环。标记的评估器使用 `--seed` 作为起始重置用的随机种子，并在各个情节中递增它。批量大小为 1 使得部署订单易于检查。缩短的 150 步限制是实验室设置。跨模型保持固定。 [标记评估脚本](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/scripts/lerobot_eval.py)

```bash
for seed in 101 201; do
  lerobot-eval \
    --policy.path=outputs/pusht-act-smoke/checkpoints/000020/pretrained_model \
    --policy.device=cpu --env.type=pusht \
    --env.observation_height=96 --env.observation_width=96 \
    --env.episode_length=150 --eval.batch_size=1 --eval.n_episodes=5 \
    --seed="$seed" --output_dir="outputs/eval-pusht-$seed"
done
```

预计检查站。每个输出目录应包含 `eval_info.json`（`overall.n_episodes` 等于 5）和已保存的视频。此单任务、批量大小一次运行中的回合顺序对应于 101-105 和 201-205。在具有编号为 20 更新检查点的 Windows CPU 冒烟运行中，两个块均返回 0/5 成功率和各 5 个视频。这些简短的试验验证了评估路径。它们几乎没有提供有关训练有素的策略的绩效的证据。

### 阅读每集的证据

将以下标准库脚本保存为 `read_eval.py`。运行 `python read_eval.py outputs/eval-pusht-101/eval_info.json 101` 并对 201 块重复。第二个参数来自你的运行命令。将该命令与 JSON 一起保留，因为此版本中的每个任务指标数组省略了重置用的随机种子。

```python
import json
import sys
from pathlib import Path

result_path, start_seed = Path(sys.argv[1]), int(sys.argv[2])
report = json.loads(result_path.read_text(encoding="utf-8"))
assert len(report["per_task"]) == 1
metrics = report["per_task"][0]["metrics"]
overall = report["overall"]
rows = zip(metrics["successes"], metrics["sum_rewards"],
           metrics["max_rewards"], strict=True)
for seed, (success, total, peak) in enumerate(rows, start_seed):
    print(f"{seed}  success={success}  reward_sum={total:.3f}  reward_max={peak:.3f}")
successes = metrics["successes"]
assert len(successes) == overall["n_episodes"]
print(f'{sum(successes)}/{len(successes)}  ({overall["pc_success"]:.1f}%)')
print("mean sum", overall["avg_sum_reward"], "mean peak", overall["avg_max_reward"])
```

成功是PushT的任务标志。当块覆盖率超过 95% 时，固定环境成功。其奖励是覆盖率除以 0.95，上限为 1。假设的四步奖励轨迹 `[0.1, 0.92, 0.4, 0.2]` 的总和为 1.62，峰值为 0.92。这次审判比最后更接近第二步。仅靠这两个汇总统计数据无法告诉你峰值何时发生。较慢的试验可能仅仅通过在目标附近花费更长的时间来获得更多。报告实际成功次数并在解释奖励金额时保持固定范围。

股票报告回答了基本的成功和奖励问题。如果你需要时间才能成功、超时或无效命令，请在环境边界处记录每次试验。记录第一个成功控制步、`terminated`、`truncated`，以及裁剪前的非有限或越界预测计数。在限制为 150 步的实验室中，完整的试验需要 15 秒的仿真时间。单独报告挂钟推断或渲染时间。如果某个进程在基准测试期间崩溃，请保留试验并在计划的分母旁边明确报告基础架构错误。

### 在权重保持固定的情况下改变执行范围

通过将循环设置为 `for seed in 101; do`、添加 `--policy.n_action_steps=1` 并使用 `--output_dir="outputs/eval-pusht-replan1-$seed"` 来重复第一个块。保持检查点、渲染设置、步骤限制和剩余参数固定。标记的评估配置使用策略 CLI 覆盖加载检查点。权重和 16 槽位预测保持不变，模型现在会查询每个报价。 [标记评估配置](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/configs/eval.py)

将试验 101 与试验 101 进行比较，然后继续执行该块。如果两个版本在第一次接触之前表现相似，然后又分开，请检查下一次重新计划及其效果。如果两者都在控制步 0 处将代理发送离开块，则首先检查输入并发出操作。浏览视频并标记最早可见的失败阶段，例如接近、第一次接触、运输或对准球门。然后在该控制步周围添加一条狭窄的轨迹，其中包含位置、命令目标、队列年龄和奖励。如果该跟踪涉及转换，请修复它，重新运行已知运动测试，并在更改架构之前重复相同的种子。

对于种子 101-105 上的两个执行范围，CPU 烟雾比较返回 0/5。在种子 104 上，峰值奖励从 0.275 上升到 0.288，而总奖励从 8.636 下降到 7.555，每个查询一个操作。该种子是检查部署的地方。仅凭分数无法确定接触后发生的情况，也无法确定哪个执行范围在训练有素的检查点上效果更好。

## 报告试验层面的不确定性

比较策略时使用匹配的重置。在说明性块中，四步策略仅在 101 上成功，一步策略在 101 和 104 上成功。报告 `1/5` 和 `2/5`，一步版本获胜一次，并且没有反向翻转。在这些种子上观察到的差异为 20 个百分点。这可以通过一次试验来解释。在固定重置分布的独立抽取下，即使 `0/5` 的两侧 95% Wilson 区间也约为 0% 到 43%。将规定的种子块视为可重复的样本，并将任何更广泛的声明与你真正关心的重置分布联系起来。

重复一个模块以检查运行之间的变异性。重复相同的种子不会扩大不同初始条件的覆盖范围，因此在调整后使用额外的未更改的重置来进行最终估计。如果你有足够的独立采样种子对，请在估计差异的不确定性时对整个种子对重新采样。一次推出的帧是相关的，并且仅提供一个成功标志。保留故障类别和计数，以便类似的聚合仍然可以显示不同的行为模式。

## 将方法带到桌面顶点

在[桌面顶点](/zh/notes/capstone-tabletop/) 中，首先重放命令以验证一个仿真时钟上的顺序和帧。然后运行 ​​Isaac Sim 6.1.0 Franka 脚本，并在实现特征映射时对保留的日志进行模拟评分。 ROS 回放使用 Ubuntu 24.04 和 Jazzy。 LeRobot 0.4.3 PushT 单独运行并演示其自己的观察-行动合约。将 Franka 连接到策略需要一个用于坐标系、动作模式和单位、夹具约定、相机变换和控制周期的显式适配器。在训练之前，使用一种已知的运动和夹具转换来测试适配器。

对于离线模仿评估，通过策略及其保存的处理器回放每个保留的情节记录的观测结果。重置回合之间的历史记录。将在控制步 `t` 处发布的预测与以原始单位记录的该控制步的操作进行比较。报告连续动作的每通道平均绝对误差 (MAE) 和离散命令的夹具一致性。例如，连续控制步上 0.02 rad 和 0.04 rad 的绝对误差使该关节的插曲 MAE 为 0.03 rad。平均情节分数如此长的轨迹不占主导地位。与始终发出每个关节的训练中值和最频繁的训练夹具命令的基线进行比较。记录的观测结果永远不会响应策略的错误。闭环部署根据策略自己的命令推进仿真器，并测量它是否恢复并完成任务。

该实验室中的所有运动都是模拟的。真正的硬件需要自己的校准、受控工作空间、紧急停止、命令和速率限制以及保守初始条件下的监督验证。

## 练习

### 诊断第一偏差

保留行动错误会下降，而推出成功则取决于匹配的种子。新策略错过了第 11 号控制步附近的块。如何区分过时的排队命令与观察或缩放错误？

<details>
<summary>解决方案</summary>
<p>检索第一个不同命令的观测结果和原始目标，并记录预测该命令的时间。使用已知目标检查已保存的处理器，并在单步执行范围内重复相同的种子。如果频繁的重新计划可以纠正偏差，请调查计划的新鲜度。如果两者从验证合同的新视图发出错误命令，请检查第一个非演示状态的覆盖范围。离线评估中记录的观测结果不受策略错误的影响。</p>
</details>

### 解释配对结果

在 10 次匹配的重置中，策略 A 在 3 次上成功，B 在 4 次上成功。他们只分享一项成功。每个方向有多少次试验翻转，为什么要保留这些信息？

<details>
<summary>解决方案</summary>
<p>B 单独获得三颗种子，A 单独获得两颗种子。他们都成功了一次，都失败了四次。观察到的净收益是一粒成功，但有五粒种子翻转。检查这五次重置的区别，然后在更大的未受影响的集合上测试比较。</p>
</details>

## 常见的误解

- 峰值奖励就是成功率。峰值奖励描述了部署中的最佳任务进度。使用仿真器的成功标志进行试验计数。
- 低离线错误保证恢复。从相同的重置开始并运行策略自己的操作。它可能会遇到专家日志从未包含的观测结果。
- 仿真器运行符合物理控制期限。即使推理花费的时间比实际经过的时间中的那个控制步更长，仿真时间也可以提前一个控制步。

## 总结

使用已知的运动检查传感器和动作语义。报告匹配重置的分子和分母，然后在更改模型之前检查第一个故障阶段。保留每个结果的种子列表和执行计划，以便其他开发人员可以重现比较。
