---
title: "理解机器人学习数据集"
topic: "LeRobot"
order: "091"
description: "检查记录的观测结果和命令，审核其时间安排，并按事件划分。"
prerequisites: "Python 和基础监督学习"
minutes: 35
---

## 决定一行所教的内容

推动策略可能会在实现出色的持有损失的同时学会为时已晚的移动。相邻的相机帧看起来很相似，并且推动者通常会多次追逐同一个目标。在训练和测试中移动标签或分割相邻行，每个张量仍可能具有正确的形状。你的第一个交付成果是你可以在安装任何东西之前进行的审核。选择一个情节，跟踪观察到其发出的命令和下一个状态，然后显示该情节及其训练窗口保持在分割的一侧。

LeRobot 存储和加载演示并使用它们进行学习。在独立的 PushT 仿真器中，圆形代理将 T 形块移向目标。从公共跟踪开始，这样你既不需要仿真器进程也不需要硬件。该轨道使用 LeRobot v0.4.3 并固定存储格式为 v3.0 的 PushT 修订版。修订版标识了确切的数据，而格式版本则告诉读者如何打开它。 [LeRobot 发布](https://github.com/huggingface/lerobot/releases/tag/v0.4.3) · [PushT 数据集元数据](https://huggingface.co/datasets/lerobot/pusht/blob/b1c3ecbae7f244acc039a3dbc255a00dad1372b9/meta/info.json)

## 将一集视为轨迹

情节从重置开始，到结果或收集截止时结束。控制步 `t` 处的行将决策之前可用的观测结果与该控制步处发出的命令配对。该命令产生到下一个观察的转换。 `next.reward` 等字段描述了该转换。它们可以帮助你审核轨迹，但提供生成的图像或奖励作为 `t` 的输入可以提供来自其自身未来的策略信息。

![并排显示两个 PushT 回合。每行将命令前的观测结果与该时间点的命令配对。时间戳在第二集中重置，完全保留在保留的分裂中。](/assets/lerobot-episode-timeline.svg)

阅读图中的每个控制步以查找与观察相关的命令。继续关注该情节以查找受该命令影响的观测结果。两个复位都从零开始行时钟，因此每当你使用 `frame_index` 或 `timestamp` 时，`episode_index` 都是地址的一部分。

| 领域 | 如何在PushT中解释它 |
| --- | --- |
| `observation.image` | RGB 视图。该数据集存储视频中的帧并将其形状声明为高度×宽度×通道。 |
| `observation.state` | 测量的代理位置，两个坐标。 |
| `action` | 命令目标位置，仿真器 512 单元工作空间中的两个坐标。形状相同并不意味着意义相同。 |
| `episode_index`, `frame_index`, `timestamp` | 回合 ID、回合本地步骤和回合相对时间（以秒为单位）。在 10 Hz 时，一帧控制步为 0.1 秒。 |
| `index`, `task_index` | 全局行索引和任务元数据的键。 |

第一实际行存储测量位置 `[222, 97]` 和绝对目标 `[233, 71]`。它们的区别是 `[11, -26]` 工作空间单位。将差异作为操作发送会要求仿真器瞄准 `(11, -26)`。下一行的记录位置约为 `[225.25, 89.31]`，接近目标的一半。精确的相等需要在该滴答声上进行瞬时运动。要诊断延迟，请检查围绕目标发生决定性变化的运动何时开始。

版本 3 将许多回合打包到共享 Parquet 和视频碎片中。回合元数据给出了每个摄像机的行范围和视频偏移量。如果一集在 MP4 中从 12.4 秒开始，则其在集时间 0.3 秒处的行请求视频时间 12.7 秒。在 MP4 中寻找 0.3 秒可以默默地选择不同的场景。使用数据集加载器进行此连接。存储模式描述了 96 × 96 × 3 图像，而加载器提供通道优先张量。 [标记数据集实现](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/datasets/lerobot_dataset.py) · [PushT 行动和观察空间](https://github.com/huggingface/gym-pusht#description)

对于记录器或导出器，只要传感器异步运行，就将采集时间戳与常规行时间戳分开保存。在示例性连接中，控制步 7 在仿真时间 0.700 秒处发送命令。可用图像的采集时间为 0.671 秒和 0.715 秒。如果该图像已可供控制器使用，则年龄预算为 40 毫秒，请选择 0.671 秒。它是 29 毫秒前的图像，距离最近的图像来自未来。如果预算为 20 毫秒，则将样本标记为缺失或遵循明确的丢弃规则。前一帧连接保留了因果关系，但在帧丢失时提供较旧的观测结果。等待新的图像会在你采取行动时提供更新鲜的输入和变化。将时序保持在一个仿真时钟中，并在其自己的边界上测量每个延迟。 [桌面抓包合约](/zh/notes/capstone-tabletop/)

## 实验室·离线审核分片

在虚拟环境中使用 `python -m pip install pyarrow` 安装 PyArrow。将[固定的 PushT Parquet 碎片](https://huggingface.co/datasets/lerobot/pusht/resolve/b1c3ecbae7f244acc039a3dbc255a00dad1372b9/data/chunk-000/file-000.parquet) 下载为 `file-000.parquet`。下面的可运行 Python 仅读取该本地文件。它既不需要 PyTorch，也不需要视频解码。

```python
from argparse import ArgumentParser
from collections import defaultdict
from math import isclose, isfinite

import pyarrow.parquet as pq

parser = ArgumentParser()
parser.add_argument("shard", nargs="?", default="file-000.parquet")
parser.add_argument("--holdout", type=int, default=20)
args = parser.parse_args()
columns = ["episode_index", "frame_index", "timestamp",
           "observation.state", "action"]
episodes = defaultdict(list)
for row in pq.read_table(args.shard, columns=columns).to_pylist():
    episodes[row["episode_index"]].append(row)

for episode, rows in episodes.items():
    for tick, row in enumerate(rows):
        location = (episode, tick)
        assert row["frame_index"] == tick, location
        assert isclose(row["timestamp"], tick / 10, abs_tol=1e-4), location
        for key in ("observation.state", "action"):
            assert len(row[key]) == 2 and all(map(isfinite, row[key])), (location, key)

ids = sorted(episodes)
assert 0 < args.holdout < len(ids)
train_ids, held_out_ids = ids[:-args.holdout], ids[-args.holdout:]
assert set(train_ids).isdisjoint(held_out_ids)
print(f"{len(ids)} episodes, {sum(map(len, episodes.values()))} rows")
print(f"train {len(train_ids)}, held out {len(held_out_ids)}")
for row in episodes[ids[0]][:5]:
    print(row["frame_index"], f'{row["timestamp"]:.1f}',
          row["observation.state"], "->", row["action"])
```

另存为 `audit_pusht.py` 并运行 `python audit_pusht.py`。该课程对固定文件的测量审核发现了 206 集和 25,650 行。第一行应打印 `0 0.0 [222.0, 97.0] -> [233.0, 71.0]`。该代码假设该文件包含从零帧开始的完整轨迹。对于一般的多分片数据集，在应用连续性检查之前找到完整的片段。如果断言触发，请按原始顺序检查报告的事件及其邻居。按损坏的时间戳排序可以消除记录器或读取器错误的证据。

改变检查器的一项输入。在脚本副本中将 `tick / 10` 更改为 `tick / 9`。第 0 次事件中的预期第一次故障是第 1 次控制步。其存储时间约为 0.100 秒，而修改后的假设给出 0.111 秒，超出了 0.0001 秒的容差。解释故障后恢复 10 Hz。比较前五个状态-目标对，并询问该状态是否正在跟踪目标或只是复制目标。明显规律的行节奏仍然可以隐藏冻结的相机或延迟应用的命令。

### 检查解码的操作窗口

使用[录制](/zh/notes/lerobot-recording/) 中的环境和[训练](/zh/notes/lerobot-training/) 中的公共数据路径，检查第 0 集内的两个窗口。此可选步骤读取视频并显示存储的行如何成为训练示例。另存为 `inspect_pusht.py` 并从训练实验室目录运行它。

```python
from lerobot.datasets.lerobot_dataset import LeRobotDataset

dataset = LeRobotDataset(
    "lerobot/pusht",
    root="./data/pusht-v3-pinned",
    revision="b1c3ecbae7f244acc039a3dbc255a00dad1372b9",
    episodes=[0],
    delta_timestamps={"action": [0.0, 0.1, 0.2, 0.3]},
    video_backend="pyav",
)
for index in (0, len(dataset) - 1):
    row = dataset[index]
    image = row["observation.image"]
    print(row["frame_index"].item(), tuple(image.shape),
          float(image.min()), float(image.max()))
    print(row["action"].tolist(), row["action_is_pad"].tolist())
```

预期图像形状为 `(3, 96, 96)`，解码值为 `[0, 1]`。不匹配要求在打开训练日志之前检查解码和布局。 LeRobot 将时间偏移转换为步数偏移，将索引固定到回合边界，并使用 `action_is_pad` 标记填充槽。如果回合在第 79 帧结束，则从 77 开始的窗口会加载带有掩码 `[False, False, False, True]` 的 `[77, 78, 79, 79]`。在对固定数据的 CPU 检查中，第 0 集在第 160 帧结束。最后一个样本显示了 `[164, 355]` 和掩码 `[False, True, True, True]` 的四个副本。 [训练章节](/zh/notes/lerobot-training/)追溯ACT如何使用这款掩码。 [标记偏移和填充实现](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/datasets/lerobot_dataset.py)

## 选择一个测试预期泛化的分割

最后 20 集 PushT 就是一个坚持的例子。即使每个输入行仅出现一次，随机行拆分也可能会泄漏。每个样本都会收到来自相邻蜱的多个标签。

```text
One episode                  tick:    38   39   40   41   42
Window at 38 assigned to train       a38  a39  a40  a41
Window at 39 assigned to holdout           a39  a40  a41  a42
                                           |----shared----|
```

保留示例的四个标签中的三个已经出现在训练中。将回合放在一起。如果 ID 0-7 共享一个收集会话，8-15 共享另一个收集会话，并且 16-19 来自第三个相机支架，则将 16-19 测试传输到该支架。要使用相同的安装测试重复重置，请在该安装下收集多个会话并保留整个会话。记录原始 ID 和每次拆分旨在测试的声明。

即使不相交的分割也可能通过拟合变换泄漏信息。如果训练 x 目标为 100 和 200，而保留包含 500，则训练平均值为 150。将所有三个目标合并得到 266.7，因此保留会更改每个标准化训练目标。为真正的离线实验具体化仅训练的数据集，并在两个分割上使用其统计数据。在此版本中，`episodes=[...]` 限制了示例，而元数据统计信息仍然可以描述父数据集。带标签的 `split_dataset` 帮助程序聚合所选回合的统计数据并重新索引其 ID。保留原始拆分清单。 [标记数据集分割实现](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/datasets/dataset_tools.py)

## 练习

### 调试一键连接

记录器在 0.2 秒时测量到 x = 200，然后发送 x 目标 230。在 0.3 秒时，状态为 212，目标更改为 250。导出将 `(212, 230)` 放在第一行。修复该对并解释为什么时间戳审核仍然可以通过。

<details>
<summary>解决方案</summary>
<p>0.2 秒处的行应为 (200, 230)，0.3 秒处的行应为 (212, 250)。错误的导出使用第一个命令的结果作为其输入。错误连接后可以重新生成常规时间戳。检查已知目标更改周围的原始捕获和指令时间戳，然后修复上游连接。</p>
</details>

### 为新的相机位姿设计一个支架

两个操作员在摄像机支架 A 和 B 上进行记录。如果你想测试在 A 上训练的策略是否适用于 B，哪些片段会被保留？坚持者应该有自己的标准化器吗？

<details>
<summary>解决方案</summary>
<p>将每个 B 集保留在一起。将观察和动作统计数据与 A 训练集相匹配，并将这些相同的转换应用于 B。记录每组中的原始 ID 和操作员计数。如果你反复调B，请保留另一组以进行最终的转移索赔。</p>
</details>

## 常见的误解

- Parquet 文件是一集。回合元数据寻址共享分片内的范围。
- 匹配的形状建立语义。代理位置和目标位置都有两个坐标。独立检查角色、单位和时间安排。
- 每个重复的目标都是填充。示威者可能会持有一个目标数个控制步。使用加载程序的边界掩码来识别合成槽。

## 总结

情节是通过控制循环的因果跟踪。审核行结构、检查解码窗口并保留拆分后的原始 ID 和统计信息。将相同的“先观察后行动”惯例带入[录音](/zh/notes/lerobot-recording/) 和[桌面顶点](/zh/notes/capstone-tabletop/)。
