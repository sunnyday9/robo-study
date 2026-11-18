---
title: "采集并检查示范数据"
topic: "LeRobot"
order: "092"
description: "编写一个小型模拟数据集并验证每个保存的帧的含义。"
prerequisites: "回合结构和Python基础"
minutes: 45
---

## 让录音机证明其顺序

生成一个在磁盘上看起来健康并教导错误行为的数据集很容易。记录器可以将命令附加到显示其效果的帧。文件计数检查将会通过，因为每个控制步仍然贡献一张图像、一个状态和一个操作。在要求人员记录演示时间之前，在收集器中构建诊断输入。在此实验中，你的目标是可以重新打开的两个片段，以及显示已知目标更改进入文件的位置以及测量位置首先响应的位置的跟踪。

## 选择生成操作的内容

在远程操作中，一个人驱动引导臂或另一个输入设备，而跟随者执行命令。优秀的操作员可以演示接触和恢复动作，而这些动作的编程成本很高。输入仍然经过校准、坐标转换、限制以及潜在的特定于接口的处理器。记录到达控制器的内容。如果用户请求夹具值为 1.1，并且命令处理器将其钳制为 1.0，则标准行为克隆的所需目标为 1.0。如果你想了解运算符达到限制的频率，请单独保存原始请求。

脚本化部署以代码形式计算命令。当你需要可重复的移动或想要隔离一项更改的影响时，请使用脚本。如果一个完美的直线脚本的覆盖范围不包括偏离中心的物体位姿，那么它仍然会产生脆弱的训练数据；人类可以提供回收率，但操作员也可以从几乎相同的观测结果中证明不兼容的策略。随机命令流有助于管道检查，因为它会执行一系列操作值。 [培训实验室](/zh/notes/lerobot-training/) 使用公共 PushT 演示进行任务监督。 [LeRobot 在 v0.4.3 处记录入口点](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/scripts/lerobot_record.py)

| 采集步骤 | 保存什么 |
| --- | --- |
| 重置 | 情节 ID、任务和出处，例如仿真器种子或操作员会话。 |
| 观察并采取行动 | 预动作摄像机和状态，以及在任何剪辑后实际发送的命令。 |
| 结束回合 | 结果和结束原因。时间限制和任务成功回答了不同的问题。 |

### 将保存边界置于决策处

在固定仿真器中，每个环境步骤都会驱动代理朝向绝对的两坐标目标。控制环路将仿真时间提前 0.1 秒。在其中，仿真器在 0.01 秒物理子步上应用位置/速度反馈控制器。这些比率描述了模拟工作。如果在主机上写入一帧需要 250 ms，则下一个 PushT 步骤仍会提前 0.1 s 的仿真时间。在实时机器人上，阻塞写入可能会导致物理系统继续移动时错过最后期限。缓冲写入器可以避免阻塞，但其队列需要容量和明确的策略来保存或删除样本。 [固定健身推包](https://pypi.org/project/gym-pusht/0.1.6/)

```text
reset(seed) --> obs[0]
                  |
tick 0     target[0] = command(obs[0])
           add_frame(obs[0], target[0])
           step(target[0]) --------------> obs[1], outcome[0]
                                              |
tick 1     target[1] = command(obs[1]) <-------+
           add_frame(obs[1], target[1])
           step(target[1]) --------------> obs[2], outcome[1]
                                              |
           if done: save_episode() <----------+
```

第二个观测结果属于第二个决定，尽管第一个命令产生了它。最终结果属于刚刚运行的转换。如果在缓冲帧之后但在执行操作之前发生异常，则将该事件视为不完整。循环结束后提交整个回合。最终确定会关闭写入器，以便可以读回已完成的分片。可加载文件是一个结构检查点，重新打开它使你有机会将持久值与实时循环中的跟踪进行比较。

## 实验室·记录两个模拟片段

在新的工作目录中使用带有 Python 3.12 的 Linux Bash shell。该命令安装 CPU 轮。记录器直接将图像存储在 Parquet 中。后面的训练实验室从公共 PushT 数据集中读取视频并使用 PyAV 解码器。如果安装在缺少 `Python.h` 的情况下构建 `evdev` 失败，请使用带有开发头文件的 Python 发行版，或者安装发行版的匹配头文件和 C 编译器。 [标记安装指南](https://github.com/huggingface/lerobot/blob/v0.4.3/docs/source/installation.mdx) · [PyTorch CPU 轮子](https://pytorch.org/get-started/previous-versions/#v271) · [PushT 软件包](https://pypi.org/project/gym-pusht/0.1.6/)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install torch==2.7.1 torchvision==0.22.1 \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install 'lerobot[pusht]==0.4.3' 'gym-pusht==0.1.6'
python -c 'from importlib.metadata import version; print(version("lerobot"))'
```

将 Python 保存为 `collect_pusht.py` 并从同一 shell 运行 `python collect_pusht.py`。默认值保留原始的两个随机部署。第二种模式保持初始 x、y 目标，然后在选定的控制步处更改一个水平目标。两种模式下的架构和环境是相同的。为每次运行选择一个新的输出目录。种子和截止是运行记录的一部分。此示例在本地运行，无需物理机器人或集线器上传。

```python
from argparse import ArgumentParser

import gymnasium as gym
import gym_pusht  # Registers PushT.
from lerobot.datasets.lerobot_dataset import LeRobotDataset

parser = ArgumentParser()
parser.add_argument("--output", default="pusht-qa")
parser.add_argument("--jump-tick", type=int, choices=range(1, 19))
args = parser.parse_args()

env = gym.make("gym_pusht/PushT-v0", obs_type="pixels_agent_pos",
               render_mode="rgb_array", max_episode_steps=20)
dataset = LeRobotDataset.create(
    "local/pusht-qa", root=args.output, fps=10, use_videos=False,
    features={
        "observation.image": {"dtype": "image", "shape": (96, 96, 3),
                              "names": ["height", "width", "channel"]},
        "observation.state": {"dtype": "float32", "shape": (2,),
                              "names": ["x", "y"]},
        "action": {"dtype": "float32", "shape": (2,), "names": ["x", "y"]},
    },
)
try:
    for seed in (11, 12):
        obs, _ = env.reset(seed=seed)
        env.action_space.seed(seed)
        start = obs["agent_pos"].astype("float32").copy()
        target = start.copy()
        target[0] += 20 if start[0] <= 256 else -20
        tick = 0
        terminated = truncated = False
        while not (terminated or truncated):
            if args.jump_tick is None:
                action = env.action_space.sample()
            else:
                action = (start if tick < args.jump_tick else target).copy()
            assert env.action_space.contains(action)
            dataset.add_frame({
                "observation.image": obs["pixels"],
                "observation.state": obs["agent_pos"].astype("float32"),
                "action": action,
                "task": "Push the T into the goal",
            })
            obs, _, terminated, truncated, info = env.step(action)
            tick += 1
        dataset.save_episode()
        print(seed, tick, info["is_success"], terminated, truncated)
finally:
    dataset.finalize()
    env.close()

saved = LeRobotDataset("local/pusht-qa", root=args.output)
assert saved.num_episodes == 2
print(saved.num_frames, saved[0]["observation.image"].shape)
if args.jump_tick is not None:
    for tick in range(args.jump_tick - 1, args.jump_tick + 2):
        row = saved[tick]
        if row["episode_index"].item() != 0:
            break
        print(tick, f'{row["timestamp"].item():.1f}',
              row["observation.state"].tolist(), "->", row["action"].tolist())
```

最初的随机运行在课程记录器检查中编写并重新打开了两集和总共 40 帧。每集上限为 20 步。预计形状为 `(3, 96, 96)` 的解码图像。使用 [分片审核](/zh/notes/lerobot-data/) 运行 `python audit_pusht.py pusht-qa/data/chunk-000/file-000.parquet --holdout 1` 以验证连续性。一集的坚持者对这场比赛进行了审查。它太小，其行为也太人为，无法估计泛化能力。打印的字段是种子、保存的步骤、成功、终止和截断。在训练集合中，将它们写入由情节 ID 键入的清单，并保留任何中止或重试原因。如果无法重新打开文件，请在检查渲染器之前检查该回合是否已保存且 `finalize()` 是否已运行。 [标记数据集编写器](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/datasets/lerobot_dataset.py)

### 将目标更改移动一控制步

```bash
python collect_pusht.py --jump-tick 5 --output pusht-jump-5
python collect_pusht.py --jump-tick 6 --output pusht-jump-6
```

种子和目标位移在这些运行中是固定的。第一次运行时打印的动作应在 0.5 秒处发生变化，第二次运行时应在 0.6 秒处发生变化。在对固定包进行的 Windows CPU 检查中，种子 11 的 x 目标在控制步 5 处从 103 更改为 123，而测量的 x 仍然读取 103。在控制步 6 处，测量的 x 读取 108.91。在第二次运行中，两个事件都晚了一个控制步。另一颗种子的确切反应取决于动力学和接触。首先查找预期行上的目标更改，然后查找状态开始响应的位置。如果位置已在更改行上响应，请将传递到 `add_frame` 的状态与 `step` 返回的状态进行比较。如果只有图像出现移位，请与状态信号分开检查相机排序、覆盖和缓冲。修复后重新运行相同的种子并跳转控制步，以便诊断保持可比性。

在硬件上，通过特定于硬件的校准和运动限制来调整探头。验证排序和边界，保留原始采集时间戳，并检查小型飞行员中的冻结帧、延迟命令和饱和度。对于[桌面回放合约](/zh/notes/capstone-tabletop/)来说，一次仿真时间权限就足够了。当流来自不同设备时，在导出到固定速率数据之前，确定它们的时钟如何对齐并报告丢失或过时的帧。单个标称 FPS 字段无法报告该偏差。

## 练习

### 分别诊断图像和状态

在控制步 5 处，目标发生变化，图像显示代理已经在运动，并且保存的数字位置在控制步 6 处首先发生变化。接下来你将收集哪条轨迹？

<details>
<summary>解决方案</summary>
<p>在促进物理进步的调用之前和之后记录图像采集时间戳和帧标识符。将它们与保存的状态和指令时间戳进行比较。检查视在运动是目标叠加还是实际运动。如果保存的图像来自该步骤之后，请修复图像关联并重复相同的目标更改探测。</p>
</details>

### 计划复苏示范

只要脚本专家集中联系该块，它就会成功。学到的策略往往首先会触及一个角落，然后继续朝错误的方向推进。你的下一次录音应该包括什么？

<details>
<summary>解决方案</summary>
<p>从偏离中心的位置开始一些演示，并包括在初始角落触碰后成功恢复。记录重置条件并描述恢复阶段。将原始的简单案例作为基线，然后使用偏离中心的接触进行单独的重置，以测试附加数据是否有帮助。</p>
</details>

## 常见的误解

- 更长的录音总是能提供更多信息。有针对性地覆盖困难方法和恢复可以增加许多重复的简单重置从未表现出的行为。
- 成功的保存证明了因果顺序。作者验证了特征结构。受控目标变化可让你测试与观察到的运动的关联。
- FPS 衡量刻录机运行的速度。它在此处定义数据集的控制步间距。实际经过的时间和错过的最后期限需要自己的衡量标准。

## 总结

记录决策时可用的状态、发送的命令以及结果的结束条件。保存并重新打开短回合，然后用已知的输入更改来挑战录音机。一旦你可以在存储的文件中找到更改，请使用具有足够任务和恢复覆盖范围的轨迹来[训练策略](/zh/notes/lerobot-training/)。
