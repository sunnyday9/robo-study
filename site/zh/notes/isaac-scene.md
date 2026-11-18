---
title: "搭建并检查仿真抓取场景"
topic: "Isaac Sim"
order: "082"
description: "通过铰接式机器人、反馈控制器和接触物理系统跟踪 USD 舞台上的立方体交接。"
prerequisites: "工作的 Isaac Sim 6.1.0 工作站和基本坐标系"
minutes: 45
---

## 从任务契约开始

当木块留在桌子上时，手臂可以完成每个命令的动作。拾放开发人员需要解释这两种历史的分歧之处。从一个固定底座的手臂、两个手指、一个刚性立方体、一个平坦的支撑物和一个目标开始。当立方体升起、到达目标区域并在释放后停留在那里时接受尝试。从一开始就将手臂和立方体的测量分开。现有的 Franka 示例使用地平面作为支撑，因此表面位于零高度。它的独立目标是一个没有碰撞器的可见标记。向标记添加碰撞会将任务从放置在平坦表面上更改为接触另一个物体。

## 构建场景并验证解决了什么问题

USD 层存储创作的意见，例如转换或参考。阶段将这些意见组合到应用程序使用的层次结构中。 prim 是该层次结构中的一个地址。引用将资产的原始子树带入所选路径的舞台。任务层可以放置机器人或覆盖属性，同时源资产保持共享。这种分离使你可以使用机器人资产的两个版本重现相同的任务，并准确检查哪个版本发生了变化。它还引入了一个调试问题：你正在查看源属性、本地覆盖还是从实时模拟读取的值？

```text
Franka USD asset -------- reference -----+
Task layer: spawn, support, target ------+--> composed stage
                                              /World/robot
                                              /World/Cube
                                              /World/PlaceTarget
                                              (plus static support)
                                                  |
                                                  v
         controller <-- measured arm state <-- PhysX step
              |                                ^      |
              +--- desired joint targets -----+      +--> cube pose
                                                           outcome gate
```

显示的路径来自独立示例。可见的机器人是几何组成的证据。关节和碰撞器也必须可供解算器使用。该图的底部显示了一个步骤的两个单独的输出。测量的工具和夹具状态会通知下一个命令，而立方体位姿会告诉你任务是否正在运行。你可以在停止时调试丢失的参考，并仅在步进后诊断驱动器或抓取器。

在将变换解释为距离之前，请检查舞台的上轴和每单位米。具有不同单位的引用资产需要校正变换或兼容资产。仅阶段元数据不会自动重新调整每个引用的资源。检查立方体的世界姿态，因为平移父项也会移动子项，且本地平移不变。在脚本编辑器中，加载示例后，这个小型检查将针对组合阶段运行。如果检查交互式示例，请使用舞台面板中的实际路径。 [OpenUSD 基本面](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/omniverse_usd/open_usd.html) · [OpenUSD 线性单位](https://openusd.org/release/api/group___usd_geom_linear_units__group.html) · [坐标系](/zh/notes/coordinate-frames/)

```python
import omni.usd
from pxr import UsdGeom

stage = omni.usd.get_context().get_stage()
cube = stage.GetPrimAtPath("/World/Cube")
print("up:", UsdGeom.GetStageUpAxis(stage))
print("m/unit:", UsdGeom.GetStageMetersPerUnit(stage))
if not cube.IsValid() or not cube.IsDefined():
    raise RuntimeError("Find the composed cube path in the Stage panel")
world_pose = UsdGeom.XformCache().GetLocalToWorldTransform(cube)
print("composed cube center in stage units:", world_pose.ExtractTranslation())
```

在停止时使用此功能来检查创作的起始位姿。对于运动轨迹，请使用示例的实时刚体状态读取器。机器人安装座上定义的 prim 只是参考的第一次检查。如果子树不完整，请检查预期的后代链接和关节以及任何资产解析错误。

| 部分场景 | 它有什么贡献 | 检查什么 |
| --- | --- | --- |
| 手臂关节 | 通过关节连接的刚性连接并作为一个系统进行求解 | 固定底座、关节根、关节名称、轴、限制和初始位姿 |
| 联合驱动 | 跟踪位置或速度目标的驱动 | 刚度、阻尼、作用力限制和测量的关节运动 |
| 立方体和支撑 | 静止在静态碰撞器上的动态物体 | 立方体质量、碰撞形状、接触摩擦和稳定的静止位姿 |
| 工具架和控制器 | 抓取器的参考位姿以及将位姿目标转变为联合目标的方法 | 工具到抓取的偏移、打开和闭合的手指运动以及相位超时 |

URDF 描述了机器人的连杆、关节、惯性属性和几何形状。 Isaac Sim 的进口商将其转换为美元。对于不同的手臂，如果需要，请启用 `isaacsim.asset.importer.urdf` 并按照该版本的文件 → 导入教程进行操作。进口后检查美元。验证基础约束并在模拟中轻轻地命令一个关节，然后观察哪个连杆移动以及朝哪个方向移动。保留包装好的 Franka USD 及其匹配的控制器配置作为下面的基线。 [NVIDIA URDF工作流程](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/importer_exporter/import_urdf.html)

## 设计相变

将任务分解为在立方体上方接近、张开手指下降、关闭、提升、转移、原地下降、打开和撤退。每个阶段都需要一个可观察的退出条件和超时。固定延迟很容易原型化，但如果关节被阻塞，计时器可能会将夹具以错误的位姿发送到下一阶段。反馈可以等待充分对准和低速。它需要合理的容差和超时，以便停滞的机器人产生诊断而不是永远等待。

6.1.0 示例使用 cuMotion RMPflow 控制器进行手臂运动和机器人特定的夹具控制器。目标是指抓握位姿。所配置的工具框架可以从该抓握点移位。如果世界空间目标涉及指尖中点，则通过将目标与工具到抓取变换的逆组合来求解工具位姿。在一个简单的说明性案例中，框架对齐，抓握点位于世界 Z 轴下方工具 0.10 m 处，工具应位于 Z = 0.125 m，以将抓握点置于 Z = 0.025 m。在旋转位姿中，偏移量随工具旋转。在尝试新的刀具偏置之前，请使用打包的配置。仍需在动态和接触下遵循联合驱动目标。到达错误、驱动器跟踪错误和滑动立方体需要不同的修复。 [NVIDIA Franka 示例](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/examples/manipulation_franka_pick_place.html)

单个逆运动学求解可以回答一个位姿是否可达。如何绕过障碍物移动到那里还没有定论。 RMPflow 根据当前状态、目标和配置的障碍物模型生成运动命令。它可以在本地绕过建模的障碍物，而当需要绕很大的弯路时，全局规划器会很有用。任务状态机单独决定何时前进。其默认工具位置和方向公差为 0.015 m 和 0.12 rad，保持至少 0.10 s。抓取和释放还可以检查夹具的完成情况。这些阈值涉及工具和手指。独立任务单独评估多维数据集。 [NVIDIA RMPflow教程](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/cumotion/tutorial_rmpflow.html) · [标记控制器源码](https://github.com/isaac-sim/IsaacSim/blob/v6.1.0/source/extensions/isaacsim.robot_motion.examples/isaacsim/robot_motion/examples/manipulation/controllers/pick_place.py)

## 实验室·检查 Franka 基线

1. 打开 Window → Examples → Robotics Examples → Manipulation → Franka Pick Place 并单击 LOAD。在舞台面板中，找到机器人、立方体和支撑物。使用“碰撞网格调试可视化”下的“窗口”→“模拟”→“调试”检查立方体并支持碰撞器。将碰撞形状与可见网格进行比较。 [NVIDIA Franka 示例](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/examples/manipulation_franka_pick_place.html) · [碰撞可视化](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/physics/simulation_fundamentals.html)
2. 单击开始选择位置。跟踪从进近、下降到接近、升起、转移、释放和撤退的顺序。 RMPflow 生成朝向工具位姿的手臂运动。该示例的阶段逻辑使用测量的反馈来决定运动何时完成。然后关节驱动器作用于机器人。手指与立方体之间的接触承载着立方体。
3. 检查手指张开并缩回后立方体是否仍靠近目标。使用示例的重置并重复。如果你更喜欢脚本运行，此可运行的 Linux 命令会从安装目录启动包含的示例。

   ```bash
   ./python.sh standalone_examples/api/isaacsim.robot_motion.examples/manipulation/pick_place.py --robot franka
   ```

检查站。在独立示例中，5 厘米立方体从 `(0.45, 0, 0.025)` m 开始，向 `(0.45, 0.35, 0.025)` m 移动。 2.5 厘米的中心高度使其底部位于平面上。消息来源检查该中心至少升高了 0.05 m。控制器完成后，它会以标称 60 Hz 步进进行 30 次连续检查，检查 XY 误差 ≤ 0.05 m、绝对 Z 误差 ≤ 0.03 m、线速度 ≤ 0.05 m/s 和角速度 ≤ 0.5 rad/s。释放时的快照可以在立方体仍在滑动时通过位置检查。例如，位于 `(0.47, 0.31, 0.025)` 的固定中心距 XY 目标约 0.045 m，满足位置限制。它还需要通过速度和升力检查。 [NVIDIA 的标记示例源](https://github.com/isaac-sim/IsaacSim/blob/v6.1.0/source/standalone_examples/api/isaacsim.robot_motion.examples/manipulation/pick_place.py)

## 追踪失去立方体的第一相

创建学习者拥有的独立脚本副本。在更新循环内，将此探针插入到现有 `if previous_phase is not controller.phase:` 块之前。标签指的是新目标影响后续步骤之前的采样状态。记录转换和偶尔的同相样本会形成一条简短的跟踪，你可以在运行之间进行比较。对于失败，还保留异常和最后几个样本。

```python
if previous_phase is not controller.phase or steps % 10 == 0:
    p, v, _ = _object_state(cube_prim)
    print(
        f"step={steps} t={controller_time:.3f} "
        f"{previous_phase.name}->{controller.phase.name} "
        f"cube={p.round(4).tolist()} speed={np.linalg.norm(v):.4f}",
        flush=True,
    )
```

想象一下在每个阶段采样的这些说明性读数。

| 控制器阶段 | 立方体中心Z | 立方体Y | 接下来要检查什么 |
| --- | ---: | ---: | --- |
| `GRASP` | 0.025 m | 0.000 m | 抓握点是否居中并且两个手指是否接触？ |
| `LIFT` | 0.096 m | 0.002 m | 电梯门已经过去了。从这里比较工具和立方体的运动。 |
| `APPROACH_PLACE` | 0.027 m | 0.070 m | 立方体高度随着手的移动而塌陷。通过转移检查抓握和接触。 |
| `RETREAT` | 0.025 m | 0.083 m | 立方体距离目标太远。仅改变释放位姿并不能解释早期的下降。 |

首先预测受控故障的第一个症状。在复制的脚本中，仅将拾取目标 Y 移动 +0.06 m，保持立方体生成并放置目标不变。在传递给 `_make_goal` 的第一个元组中进行编辑，然后从具有相同配置的新进程重新运行。偏移量超过立方体宽度的一半。预计会出现偏离中心的下降，然后是错过抓握或失败的阶段。确切的结果取决于几何形状和运动。与下跌、收盘和上涨时的股票轨迹进行比较。如果手到达移动的目标并且立方体保持在支撑高度，则位姿规划器将执行要求执行的操作。恢复已知良好的选择目标并重新运行以测试解释。

当基线本身失败时，首先对症状进行分类。在手指到达之前从平面下落的立方体指向刚体或碰撞配置。下降时工具到目​​标的较大误差需要检查目标框架、工具变换、障碍物模型和关节跟踪。如果工具放置良好，但痕迹显示在提升过程中丢失，请在重新调整手臂之前检查碰撞几何形状、摩擦、接触和夹具作用力。每次编辑后，保留成功的基线并添加最小的失败条件作为可重复的试验。

## 练习题及解答

夹具到达指定位置位姿、打开并退回。有什么证据可以证明这一集的成功？

<details>
<summary>检查你的答案</summary>
<p>检查立方体是否从支撑物上抬起，以及其测量的姿态和速度是否满足释放后的放置和沉降标准。手臂的位姿仅表明手臂到达了目标。</p>
</details>

该平面被替换为顶部 Z = 0.72 m 的工作台。你更新视觉场景，手臂在下降过程中将张开的手指压在桌面上。 5 厘米立方体的中心应该从哪里开始，还有哪些其他更改必须同意？

<details>
<summary>检查你的答案</summary>
<p>使用 Z = 0.745 m 作为该表面上的静止中心。在同一世界坐标系中更新生成、拾取和放置目标以及预期的固定高度。独立验证工作台碰撞器，使用工具偏移重新计算抓取和间隙位姿，并在请求抓取之前检查固定基臂的范围和控制器的障碍物配置。</p>
</details>

## 常见的误解

- 我看到的几何体是对撞机。解算器使用碰撞形状，它与可见网格有很大不同。检查两者。
- 完成的关闭确认了掌握。当立方体偏离中心或滑动时，手指状态可以满足控制器条件。物体的运动提供了证据。
- 更大的刚度可以修复任何错过的目标。首先将不正确的位姿请求与物理上无法到达或跟踪不良的请求分开。

## 总结

独立组成资产和任务，然后检查生成的原语和框架。在进行更改之前检测联合命令和立方体状态边界。从测量数量超出预期的最早阶段开始工作，并在每次单独修复后重新运行基线。

使用平面支撑示例作为 [桌面顶点](/zh/notes/capstone-tabletop/) 的操作基线。对于高架桌子，添加静态碰撞器并重新计算立方体相对于其顶部的生成高度和目标高度。检查手臂固定底座的范围，并将桌子包含在控制器的障碍物模型中。使用 [bridge lab](/zh/notes/isaac-ros-bridge/) 了解外部程序如何解释模拟传感器流。
