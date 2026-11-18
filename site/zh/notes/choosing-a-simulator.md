---
title: "选择仿真器并验证模型"
topic: "Simulation"
order: "080"
description: "将物理、传感和中间件问题分开，然后选择能够回答你的工程问题的最便宜的环境。"
prerequisites: "机器人模型、反馈和 ROS 2 的基础知识。"
minutes: 55
---

## 从索赔开始，而不是仿真器

假设你的室内移动机器人有时会错过转弯。你可以花一天的时间在逼真的引擎中重现房间，但如果控制器使用度数而不是弧度，单元测试将给出更好的答案。相反，网格中的点无法告诉你校准的深度相机是否看到反射墙。使用包含要测试的故障机制的最简单的模型。

| 问题 | 启动环境 | 它遗漏了什么 |
| --- | --- | --- |
| 我可以变换点、找到路线或检测截止时间错过的情况吗？ | CPU 数学夹具、跟踪重放、网格或玩具积分器 | 接触、执行器动力学和传感器真实度 |
| 我的 ROS 2 移动机器人堆栈可以使用虚拟里程计并发布适当的控制吗？ | Gazebo 与 ROS 2 配对； Jazzy 和 Harmonic 是有记录的配对 | 真实网络、电机、校准和车轮打滑行为 |
| 在受控重复试验中，策略是否比物理基线有所改善？ | 用于你显式实现的任务的匹配环境，例如 PushT 或 MuJoCo 模型 | 部署驱动程序、时序和硬件差异 |
| 我的特定相机/RTX 管道是否会从场景中生成图像和 ROS 2 元数据？ | Isaac Sim 以及支持的渲染器和桥接器 | 实际镜头、时钟、材料、运输和照明，除非明确建模 |

这些是起点，而不是可互换的后端。 [Gazebo的ROS配对表](https://gazebosim.org/docs/harmonic/ros_installation/)和[MuJoCo的仿真文档](https://mujoco.readthedocs.io/en/stable/programming/simulation.html)描述了不同的接口。 [Isaac Sim](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/requirements.html) 有硬件和发布合同。 [LeRobot](/zh/notes/robot-learning-methods/)消耗数据或兼容环境；它不是另一个物理引擎。

## 了解四种仿真时钟

```text
 physics step ──▶ scene state ──▶ sensor acquisition ──▶ observation
       ▲                                   │               │
       │                    render/update cadence          ▼
       └── hold action over steps ◀──── controller decision

 simulated time identifies a state; elapsed wall time measures execution cost
```

一次应用程序更新可以推进零、一或几个物理步骤。渲染可能比物理慢。对照可以以另一个间隔采样。将每步积分、控制节奏、虚拟采集时间和经过的执行时间视为显式输入。无头模式会移除一个窗口；这并不意味着渲染被省略。即使配置的速率匹配，消费者的操作速度也可能比生产者慢。

记录包含仿真器版本、场景修订、模型单位、解算器参数、物理步骤、观察节奏、控制周期和重置用的随机种子的清单。在比较策略时，请保持评估环境和相同的初始条件可用。比较引擎设置时，保持控制率和场景固定或明确测量它们的相互作用。

## 实验室：在安装任何东西之前测试数值假设

物体以 1 m/s² 的恒定加速度开始静止。 1 秒后，其精确位置为 0.5 m，速度为 1 m/s。简单的离散积分器根据其步长和更新顺序给出不同的结果。将其另存为 `step_check.py`：

```python
from math import isclose


def integrate(steps, velocity_first):
    position, velocity = 0.0, 0.0
    dt = 1.0 / steps
    for _ in range(steps):
        if velocity_first:
            velocity += dt
            position += velocity * dt
        else:
            position += velocity * dt
            velocity += dt
    return position, velocity


for steps in (10, 20, 40):
    explicit, velocity = integrate(steps, False)
    semi_implicit, _ = integrate(steps, True)
    assert isclose(velocity, 1.0)
    print(f"{steps:2}: {explicit:.4f}  {semi_implicit:.4f}  exact 0.5000")
```

运行前预测：位置优先版本使用旧的、较小的速度，因此它低估了行程；速度优先高估了它。 10 步时预计为 0.45 和 0.55 m。在这个特定的恒定加速度示例中，步长减半可以使误差减半。它没有建立完整刚体接触模型的收敛速度。接触可能会在离散化过程中出现或消失。

将此方法扩展到所选的仿真器。从自由移动的身体或已知的关节偏移开始；与手算进行比较。然后一次添加一个接触、摩擦和传感器噪声。如果更改物理速率，请保留控制器周期（以秒为单位）。例如，20 Hz 控制器在 60 物理 Hz 时每三步消耗一个命令，在 100 物理 Hz 时每五步消耗一个命令。在这两个实验中，每第三步更新一次就会改变两个变量，而不是一个。

## 定义什么是可转让的

使用单独的参数集进行校准和评估；适合一次记录的操作的模型可能无法预测新的负载或表面。更改合理的质量、摩擦力或传感器误差范围并报告结果的变化。随机化暴露了敏感性；它并不能证明抽样分布描述了现实。保留故障并记下任何不受支持的资产、缺失的动态或你所依赖的仿真器便利性。

如果某项功能依赖于硬件上不可用的虚拟测量（例如，精确的全局姿态或直接访问接触法线），则将其标记为预言基线。在存在真实的测量路径并进行评估之前，使用它的策略不是部署的候选者。

## 练习

你将物理步骤减半，就会发现更好的掌握。你的策略仍然每四步执行一个命令。接下来你应该做什么？

<details>
<summary>检查实验设计</summary>
<p>你更改了求解器步骤和每个命令的模拟持续时间。调整每次决策的步数，恢复原来的控制周期，保持复位和初始接触相同，再次比较。</p>
</details>

在仿真器中，60 个 RGB 帧代表模拟一秒，但渲染需要四秒。哪个数字对数据集导出者重要，哪个数字对部署预算重要？

<details>
<summary>检查时域</summary>
<p>仿真时间中的时间戳和间隔定义了数据集样本序列。每墙每秒 15 个帧描述了运行吞吐量。两者都无法证明真正的传感器或策略能够满足其端到端的最后期限。</p>
</details>

## 弘扬什么

使模型成为具有接受标准的假设。首先测试廉价的不变量，然后转移到 [Isaac 环境实验室](/zh/notes/isaac-environment/) 或在这些接口是测试的原因时使用以 ROS 为中心的仿真器。
