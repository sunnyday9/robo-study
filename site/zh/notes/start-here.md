---
title: "从这里开始：学会构建机器人，而不只是使用工具"
topic: "Orientation"
order: "000"
description: "先学机器人系统的共同基础，再按职业方向完成项目，并整理可以复现的实践成果。"
prerequisites: "基础 Python。起步不需要 GPU 或实体机器人。"
minutes: 25
---

## 机器人软件和普通软件有什么不同？

机器人感知物理世界，推断当前状态，再决定怎样行动。行动又会改变下一次观测。导航模型在离线数据上可能很准，但在实际运行时，测量可能已经过时、目标可能无法到达，电机也可能跟不上指令。机器人系统工程要解决的，就是如何让这样的闭环在物理、计算和安全约束下可靠运作。

本书假设你会写一点 Python，但不要求有机器人基础。先不必安装 ROS，也不用训练模型。你会先写一个小型仿真控制器，并弄清它为什么有效，再逐步学习几何、动力学、感知、规划、机器人软件、学习算法和现场实践。

```text
  physical or simulated world
      │ observation + frame + time
      ▼
  sensing → state estimate → plan → feedback → actuator
      ▲                                          │
      └────────── world changes as a result ───────┘

  safety limits, clocks, and test evidence cross every boundary
```

不存在称为“机器人”的单一堆栈。操纵器控制关节并处理接触。室内移动机器人估计其姿态并绕过障碍物进行导航。嵌入式工程师可能永远不会训练模型，但需要知道在最后期限内传感和驱动的行为方式。共同的想法是指定和测试连接这些层的接口。

## 先打好共同基础，再选择方向

<figure class="lesson-figure">
  <a href="/assets/figures/study-path.svg"><img src="/assets/figures/study-path.svg" width="640" height="494" loading="lazy" decoding="async" alt="四个里程碑：从仅使用 CPU 的机器人循环开始，学习运动和传感，通过 ROS 和模拟进行集成，然后构建一个专业项目。"></a>
  <figcaption>每加一层之前，先复现当前结果，再解释一个失败案例。点击图片可以查看原图。</figcaption>
</figure>

| 舞台 | 学习 | 你可以保留的证据 |
| --- | --- | --- |
| 第一步 | [机器人循环](/zh/notes/robot-loop/)，[数学和测量](/zh/notes/robot-math-and-measurement/)，[框架](/zh/notes/coordinate-frames/) | Python 运行、故意中断的运行以及对假设更改的解释 |
| 基础 | [运动与控制](/zh/#motion)、[感知与估计](/zh/#sensing)、[规划与自治](/zh/#autonomy) | 已知的正向/反向运动情况、噪声样本的估计以及检查的路线 |
| 软件集成 | [机器人软件和ROS 2](/zh/#ros-2)，[模拟](/zh/#isaac-sim)，[基础设施](/zh/#infrastructure) | 来源工作区、加盖重放证据、版本清单和可重复的失败/通过测试 |
| 应用工程 | [机器人学习](/zh/#lerobot)或[现场工程](/zh/#field)，加上相关核心 | 经过衡量的策略比较，或时间安排、调试和验证计划 |
| 作品集 | [移动机器人项目](/zh/notes/capstone-rover/) 或 [桌面操控](/zh/notes/capstone-tabletop/) | 可重现的演示、测试用例、故障分析和简洁的交接 |

Read across the common core even if you already know what role interests you. Someone implementing a planner needs enough control theory to understand an infeasible trajectory. Someone training a policy needs enough sensor and timing knowledge to catch a corrupted dataset. After the common core, use the [career map](/zh/notes/robotics-career-roadmap/) to choose depth.不要试图按顺序掌握每个专业。

## 在每个部分使用相同的开发循环

1. 指定可观察的声明。 “在已知的关节角度下，工具点位于此处”是可测试的。 “机器人能工作”则不然。
2. 建立最小基线。使用已知点、综合主题、网格或小型卷展栏。 Remove runtime layers that the current claim does not need.
3. 在边界处测量。 Record frame, units, time source, run configuration, and what you actually saw.
4. 打破一个假设。延迟读数、偏移校准、删除变换或更改截止日期。在运行之前写下预期的症状。
5. 解释一下第一个分歧。如果回放和模拟不一致，请找到最早的差异，而不是立即更改所有参数。

Keep a notebook with columns for claim, configuration, expected result, actual result, and next diagnostic.成功的运行是有用的；表明阴性对照因正确原因而失败更为有用。 Compare the scope of the evidence with the scope of the conclusion.

## 选择安装内容和时间

你可以从 [浏览器实验](/zh/demos/) 和 Python 开始。公共核心示例不需要 GPU。安装 ROS、仿真器或 ML 工具包时，请使用[环境章节](/zh/notes/infra-environments/)。不要一开始就试图让每个工具共享一个 Python 环境。

ROS 2 是中间件和工具。 Isaac Sim、Gazebo 和 MuJoCo 回答不同的模拟问题。 LeRobot是一个学习工具包，而不是仿真器。 [仿真器选择章节](/zh/notes/choosing-a-simulator/) 在 Isaac 特定实验室之前明确了权衡。 PushT 学习路径和 Isaac 桌面路径是分开的，除非你在它们之间构建和测试适配器。

## 完成这本书可以证明什么，不能证明什么

该学习路径的目标是实际工作基础：制作原型、指定其接口、测试它、调试它并解释它的局限性。仅阅读并不能提供硬件体验。模拟通过并不代表物理机器人或安全系统合格。对于硬件实践，请使用具有批准平台、培训、调试程序和授权负责操作人员的受监管实验室。使用现场章节来准备问题和工件，而不是代替监督。

要关闭一个部分，请独立显示一个小工件：没有提示，不复制预期输出，以及一个新的故障案例。如果你无法解释测试失败的原因，请重新访问相关边界。与标记为已完成的章节数量相比，这是更好的准备信号。

## 检查你的学习计划

你的笔记本电脑不支持 GPU，需要三个晚上才能访问 ROS 机器。你先做什么？

<details>
<summary>比较你的计划</summary>
<p>构建并改变第一个 Python 循环，手动检查已知的转换，并运行一个小型规划或估计示例。将预期的数据契约和故障测试带到 ROS 机器。为真正需要模拟渲染或物理的问题节省 GPU 时间。</p>
</details>

一名开发人员表示，由于仿真器任务已完成，他们已准备好操作物理手臂。还缺少什么证据？

<details>
<summary>检查证据边界</summary>
<p>硬件校准、限制、计时、故障和停止行为以及监督调试保持独立。仿真器结果仅支持所述的模拟场景。</p>
</details>

## 更深入研究的参考资料

- [现代机器人](https://modernrobotics.northwestern.edu/nu-gm-book-resource/) 以数学方式开发运动、力、规划和控制。
- [麻省理工学院欠驱动机器人](https://underactuated.mit.edu/) 更深入地开发动力学、估计和优化。
