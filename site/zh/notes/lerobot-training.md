---
title: "训练模仿学习策略"
topic: "LeRobot"
order: "093"
description: "比较 ACT 和扩散策略，训练 ACT 检查点并检查其处理器。"
prerequisites: "回合分割、PyTorch 基础知识和录音实验室设置"
minutes: 55
---

## 证明从批处理到命令的路径

<figure class="lesson-figure">
  <a href="/assets/figures/policy-workflow.svg"><img src="/assets/figures/policy-workflow.svg" width="640" height="494" loading="lazy" decoding="async" alt="记录观察-动作对，通过处理进行训练，将模型和处理器保存在一起，并在闭环中评估解码的命令。"></a>
  <figcaption>在整个工作流程中遵循一个示例。仅保存权重，忽略了在推出时赋予预测意义的转换。</figcaption>
</figure>

如果一个训练有素的推手开车到原点，你的第一个问题是它是否“选择”了原点。策略可以预测标准化坐标中的合理动作，同时控制器将这两个数字读取为绝对位置。模型还可以选择连贯的动作，并在物体移开后继续执行它。建立一个检查点来区分这些故障。可观察的目标是有限的训练更新、带有处理器的可重新加载策略，以及表明哪个观察生成了每个发出的命令的跟踪。

## 决定模型预测什么

行为克隆使用演示的动作作为监督目标。仿真器的奖励对于衡量以后的行为很有用。本讲座中的 ACT 和扩散策略是从数据集中的动作序列中学习的。在一步式策略中，你在每次观察后进行推断。在分块策略中，多个目标一起生成，这可以通过接触保持连贯的机动。预测范围是模型代表的跨度。执行范围是在再次查询策略之前实际消耗的目标数量。较长的执行范围可以节省前向传递，但会留下更多的蜱虫，由基于较旧观察的计划控制。

| 策略 | 它如何建模动作 | 看什么 |
| --- | --- | --- |
| ACT | Transformer 在一次前向传递中预测一个块。训练时间变分编码器可以使用记录的动作块。在普通推理中，模型使用零潜伏。 | 当类似的演示选择不同的方法时，检查接近接触时的犹豫。 |
| 扩散策略 | 观察条件去噪网络迭代地对动作序列进行采样。样本可以代表不同的合理操作。 | 测量采样延迟以及操作进行到一半时连续的重新计划是否一致。 |

从 ACT 开始检查管道。比较相同数据的架构，重置用的随机种子和任务指标。他们的训练损失描述了不同的目标并且具有不同的规模。 [ACT 论文](https://arxiv.org/abs/2304.13705) · [扩散策略论文和项目](https://diffusion-policy.cs.columbia.edu/) · [标记 ACT 配置](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/policies/act/configuration_act.py) · [标记扩散配置](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/policies/diffusion/configuration_diffusion.py)

### 跟随目标进入损失

对于此 ACT 实验室，一批两个样本包含形状为 `(2, 3, 96, 96)` 的当前图像和形状为 `(2, 16, 2)` 的块。每个块在偏移量 0 到 15 处预测 x 和 y。训练会将每个预测目标与相同偏移处的演示目标进行比较。在情节边界，加载程序重复边缘目标并设置填充标志，如[数据集实验室](/zh/notes/lerobot-data/) 中所示。在此版本中，ACT 将绝对误差乘以反向填充掩码，然后取张量平均值。对于一个坐标和四个槽，最后两个掩码产生的错误 `[0.2, 0.4, 0.6, 5.0]` 会产生 `(0.2 + 0.4) / 4 = 0.15`。 5.0 不提供重建梯度。两个归零的条目仍计入分母。启用变分编码器后，ACT 添加一个加权 KL 项，将学习到的潜在分布正规化为标准正态分布。诊断停顿运行时分别记录重建和 KL。 [已标记ACT损失和前向传递](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/policies/act/modeling_act.py)

扩散策略以采样的扩散时间步长构建整个动作轨迹的噪声破坏版本。对于标记的默认 `epsilon` 目标，它使用预测噪声的平方误差。在推理时，它从噪声开始，并根据最近的观测结果运行相反的过程。标记的默认值使用两个观察控制步。 16 槽预测跨越 `t − 1` 到 `t + 14`，并从 `t` 的槽开始执行。检查轨迹边缘附近的扩散策略损失时，请独立于 ACT 的行为检查其填充掩码设置。 [已标记扩散训练和采样代码](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/policies/diffusion/modeling_diffusion.py)

考虑一个演示集，其中同一块的两个有效方法以 180 和 320 的 x 目标开始。如果当前输入使预期方法不明确，则点预测可能会落在它们之间。在场景上绘制每个生成的轨迹可以显示它是否遵循有效的路线。扩散可以代表多条路线，但代价是更多的计算和跨重新计划切换路线的可能性。另一项实验是为模型提供消除歧义的任务信号，或围绕一种一致的方法调整演示。你选择的改变应该遵循你在第一个模棱两可的决定中看到的情况。

### 追踪重新计划

```text
Tick                        8      9     10     11     12
Observation available       o8     o9    o10    o11    o12
Model runs?                 yes     ·      ·      ·    yes
Issued x target             210    225    243    260    228
Plan was made at tick       8      8      8      8      12
                                ^ block deflects here
```

这是实验室 16 步预测的说明性跟踪，其中执行了 4 个步骤。在控制步 10 处，仿真器有一个新的观测结果，但策略从控制步 8 的队列中获取下一个目标。在控制步 12 处，它使用新视图重新规划。每组执行 0.4 秒的模拟行为。对于每个查询一个操作，策略可以在第 9 或 10 个控制步处响应，具体取决于何时可以观察到干扰。留意恢复和命令连续性的变化。更频繁的重新计划可以改变每个控制步的顺序，并且在时间有限的控制器上，增加延迟命令的机会。

## 实验室·训练一个小型ACT检查点

使用新的输出路径在 [LeRobot v0.4.3 环境](/zh/notes/lerobot-recording/) 中运行此 Bash 命令。第一次运行下载公共数据集，包括其视频碎片。数据章节中经过审计的分割展示了事件分区。此烟雾运行使用所有公开演示，下一章将评估新的仿真器重置。对于离线实验，使用其自己的统计数据具体化仅训练数据集。在此版本中，`dataset.episodes` 选择加载的行，而训练仍然从数据集元数据读取标准化统计信息。 [标记数据集被控对象](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/datasets/factory.py) · [标记训练脚本](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/scripts/lerobot_train.py)

```bash
lerobot-train \
  --dataset.repo_id=lerobot/pusht \
  --dataset.revision=b1c3ecbae7f244acc039a3dbc255a00dad1372b9 \
  --dataset.root=./data/pusht-v3-pinned \
  --dataset.video_backend=pyav \
  --policy.type=act --policy.device=cpu --policy.push_to_hub=false \
  --policy.pretrained_backbone_weights=null \
  --policy.chunk_size=16 --policy.n_action_steps=4 \
  --steps=20 --batch_size=2 --num_workers=0 --seed=17 \
  --log_freq=5 --eval_freq=0 --save_freq=20 \
  --output_dir=outputs/pusht-act-smoke
```

预计检查站。寻找有限的记录损失和 `outputs/pusht-act-smoke/checkpoints/000020/pretrained_model/`。这是管道冒烟测试。二十次更新为你提供了可供检查的具体工件，并且几乎没有关于所学操作质量的证据。 Windows CPU 检查完成了 20 个更新并写入了编号的检查点。然后，训练 CLI 遇到 Windows 权限错误，创建 `last` 符号链接。使用编号路径进行处理器检查和评估。该实验室的 Linux 设置并未在该检查中端到端运行。

使用第一个失败的阶段来选择下一个探针。如果加载程序在第一次更新之前显示 AV1 错误，请使用 [解码窗口检查](/zh/notes/lerobot-data/) 通过 PyAV 请求一个图像。更改型号前请检查下载和解码器。如果批次到达后损失变得非有限，请记录预处理器之前和之后的状态、动作和图像的最小值和最大值，并检查填充掩码。一旦管道工作，一个有用的训练端探测就是重复优化相同的预处理批次并观察其重建错误。如果无法适应该批次，则表明存在优化或表示错误。重复批次的成功几乎无法告诉你新的观测结果。对于真正的离线比较，请使用仅训练分割并以原始单位报告保留结果。

## 继续使用权重进行预处理

遵循从磁盘到仿真器的表示。加载程序将 RGB 图像解码为 `[0, 1]` 中的通道优先浮点数。在训练时，ACT 的策略预处理器处理输入命名、批处理、设备放置和功能标准化，包括操作目标。默认情况下，训练 CLI 使用 ImageNet 平均值和标准差来表示相机特征。状态和动作都有自己的拟合平均值和标准差。扩散策略默认为状态和动作的最小-最大缩放，因此相同的数字张量可以对应于不同的物理命令。在评估时，环境代码构造输入布局，保存的策略预处理器应用训练变换，并且保存的后处理器在仿真器调度之前反转输出变换。 [已标记 ACT 处理器](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/policies/act/processor_act.py)

对于说明性的 x 目标平均值 250 和标准差 50，模型预测 0.6 应以 `250 + 50 × 0.6 = 280` 的形式到达环境。发送 0.6 直接瞄准工作空间边缘。应用两次逆运算将产生 14,250。将整个 `pretrained_model/` 目录放在一起，以便配置和处理器状态随权重一起移动。对于可恢复训练，还保留同级 `training_state/`。记录源数据修订、原始拆分 ID、种子和功能契约。 [标记检查点编写器](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/utils/train_utils.py)

### 检查具有已知目标的处理器

训练后，从同一工作目录运行此 CPU 检查。零向量是已知的 ACT 模型空间值。结果应与固定数据集元数据中的原始操作平均值相匹配，且不超过浮点误差。该检查独立于训练的权重来训练打包的后处理器。

```python
import json
from pathlib import Path

import torch
from lerobot.configs.policies import PreTrainedConfig
from lerobot.policies.factory import make_pre_post_processors

checkpoint = Path("outputs/pusht-act-smoke/checkpoints/000020/pretrained_model")
config = PreTrainedConfig.from_pretrained(checkpoint)
_, postprocess = make_pre_post_processors(config, pretrained_path=str(checkpoint))
stats_file = Path("data/pusht-v3-pinned/meta/stats.json")
action_mean = torch.tensor(json.loads(stats_file.read_text())["action"]["mean"])
raw_target = postprocess(torch.zeros((1, 2)))[0]
print(raw_target.tolist(), action_mean.tolist())
torch.testing.assert_close(raw_target, action_mean)
```

在CPU检查中，两个打印向量大约为`[228.24, 293.99]`。对于受控故障，仅将 `raw_target = postprocess(torch.zeros((1, 2)))[0]` 替换为 `raw_target = torch.zeros(2)`。这再现了断言失败，因为它将标准化预测与绝对坐标进行了比较。如果原始检查也失败，请跟踪加载程序使用的处理器文件，并在重新训练之前比较存储的训练动作统计数据。恢复逆，然后将完整的检查点带到[闭环评估](/zh/notes/lerobot-evaluation/)，以改变队列长度，同时保持权重固定。

## 练习

### 诊断过时的计划

在控制步 32 处，ACT 策略重新计算，在控制步 33 处，块滑动。每个查询有四个操作，新观察何时可以首先影响预测？什么实验隔离了队列的贡献？

<details>
<summary>解决方案</summary>
<p>在消耗第 32-35 个控制步后，它首先在第 36 个控制步重新计划。保留权重和 16 步输出，将执行更改为每个查询一个操作，并在同一重置上比较第一个滑动后命令、后续接触和推理成本。如果两个节奏都发布同样糟糕的新计划，请调查恢复范围或观察合同。</p>
</details>

### 追踪两次损失

队友在同一数据集上比较了 0.25 的 ACT 损失和 0.12 的扩散损失。哪些证据可以让你选择在仿真器中部署的模型？

<details>
<summary>解决方案</summary>
<p>ACT 将掩蔽绝对动作误差与潜在正则化相结合。扩散的默认值预测带有平方误差的注入噪声。比较仿真器单元中保留日志的实际命令，然后比较匹配重置和固定控制计划的任务结果和推理时间。即使平均分数一致，也要检查故障轨迹。</p>
</details>

## 常见的误解

- ACT 发送完整的预测块。在实验室配置下，模型预测 16 个操作并对前四个操作进行排队。队列长度是一个推理选择。
- 每一步去噪都会让机器人前进。去噪计划是模型内部的。当发出的目标到达环境时，控制时钟提前。
- 权重包含每个预处理选择。标准化状态与处理器定义一起保存。重新加载完整的检查点并测试已知的操作。

## 总结

跟踪确切的训练目标、其标准化、模型的损失以及生成实际命令的队列。一次微小的运行就可以检查每个接口。使用已知值测试处理器并一次更改一个推理设置，以了解哪些故障来自控制器的调度。
