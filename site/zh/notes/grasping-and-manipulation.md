---
title: "抓取与操作规划"
topic: "Planning and autonomy"
order: "052"
description: "将物体位姿转变为分阶段拾取和放置，然后测试抓取如何改变规划场景。"
prerequisites: "坐标系、基本三角学以及搜索和运动规划。"
minutes: 60
---

## 计划抓握以及之后发生的事情

桌面臂必须将托盘上的块移动经过固定装置。以正确的位姿闭合夹具是一个里程碑。进场必须清理托盘，手指必须建立稳定的抓握，并且撤退必须将新的组合形状带过固定装置。孤立地看起来很出色的抓握可能会让手臂无处可退。

将抓取候选表示为相对于对象的工具位姿，加上夹具开口和接近方向。如果 `T_A_B` 将坐标从 B 映射到 A，则在观察时间计算 `T_base_grasp = T_base_object × T_object_grasp`。当在相机帧中检测到对象时，此约定也适用。预抓取通常沿着抓取框架中表示的接近轴偏移。例如，如果工具沿其正 Z 轴前进，则沿该轴向后移动 0.08 m 将创建预抓取。相反，从 Z 轴减去 0.08 m 会为倾斜抓握提供不同的点。在评估边缘和手指孔的间隙时包括感知不确定性。 [坐标框架](/zh/notes/coordinate-frames/) · [ROS 2 框架和时间](/zh/notes/ros2-frames-and-time/)

```text
Open fingers   Close and verify grip     Lift and transfer    Release
 pregrasp ---> grasp + block ----------> tool + block ------> place
                 |                            |                  |
Scene: block in world     attach block to tool link       detach to world
                              after grip evidence         after release
```

上面的线显示了运动阶段，下面的线显示了碰撞几何体何时发生变化。计划预抓握、接近、接近、验证抓握、将块附加到场景中、撤退、转移、放置并确认释放。阶段转变需要观察。模拟夹具可以报告下颌分离和接触情况。对于每个手指法向力 `N` 和静摩擦系数 `μ` 相等的简单两侧捏合，`2μN ≥ mg` 是理想摩擦模型中对称静升力的必要力平衡。偏心负载会增加扭矩，加速或接触不良会导致打滑。仅夹具完成就无法提供牢固固定的证据。在模拟中，检查分离和接触，然后在小幅提升后测量物体相对于工具的运动。

## 选择表达约束的空间

**任务空间**描述了工具位姿。 **联合空间**描述联合值。正向运动学将关节映射到工具。逆向运动学 (IK) 可以为一个目标提供多种关节解决方案，例如肘部向上和肘部向下。有些目标是无法实现的。在奇异配置附近，将关节速率映射到工具速度的雅可比行列式会失去等级或变得条件较差。在困难的方向上的一个小的笛卡尔请求可能需要大的联合改变。在实际情况下，从先前的解决方案中种子连续 IK 求解，并检查关节限制和连续性。两个关节矢量之间的直线可以使刀具路径弯曲穿过托盘壁。相反，直接笛卡尔方法可能会在最终目标之前失败，即使该目标具有有效的 IK。

常见的设计使用自由空间联合规划进行转移，并使用笛卡尔运动进行短距离受限进场和撤退。根据可达性、间隙以及是否可以规划进场和升力，对多个抓取候选者进行排名。几何路径描述了机器人将要去的地方。定时关节轨迹还描述了在速度和加速度限制内它应该出现的时间。对照新测量的关节检查启动情况，提交定时轨迹，观察跟踪误差和前进前的动作结果。在考虑其他计划之前，取消相关故障并确认由此产生的控制器和机器人状态。 [ROS 2动作](/zh/notes/ros2-communication/) · [ros2_control Jazzy关节轨迹控制器](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html)

## 当夹点变化时更新碰撞几何体

<figure class="lesson-figure">
  <a href="/assets/figures/grasp-sequence.svg"><img src="/assets/figures/grasp-sequence.svg" width="640" height="373" loading="lazy" decoding="async" alt="三个侧视图显示夹具接近未连接的块，确认抓握，并将连接的块携带通过固定装置。"></a>
  <figcaption>在握力之前，方块是世界的一部分。确认握持后，在检查转移时用手包括其形状。</figcaption>
</figure>

规划场景结合了机器人状态和几何形状、障碍物、附着体和碰撞策略。确认抓取后，将一个对象从世界位姿转换为相对于适当工具链接固定的位姿。仅允许预期的手指与物体接触。检查附加的几何形状是否有障碍物和相关的机器人链接。发布时，根据测量或模拟状态更新其世界姿态。场景中的附件会更改几何碰撞查询。真实或模拟控制器的有效负载动态和握力反馈有自己的接口。

在 ROS 2 Jazzy 上的 MoveIt 2 中，C++ `PlanningSceneInterface` 提供 `applyAttachedCollisionObject` 以将附件同步应用到 `move_group`。标头文档表明单独的场景监视器需要订阅受监视的场景才能接收更新。在使用转移轨迹之前确认规划者所看到的场景。 `MoveGroupInterface::computeCartesianPath` 返回完成分数。部分前缀对于诊断方法失败的位置非常有用。对于目标是接触目标的阶段，需要一个完整的、经过验证的方法。这些细节来自 Jazzy 来源。 [Jazzy规划-场景界面](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning_interface/planning_scene_interface/include/moveit/planning_scene_interface/planning_scene_interface.hpp) · [Jazzy笛卡尔路径界面](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning_interface/move_group_interface/include/moveit/move_group_interface/move_group_interface.hpp)

## 实验室：附加负载后传输无效

另存为 `carry.py` 并运行 `python carry.py`。在桌面的二维切片上，双连杆模型的长度为 0.45 和 0.35 m。对于目标 `(x, y)`，余弦定律给出 `cos(q2) = (x² + y² − L1² − L2²)/(2 L1 L2)`。选择正 `q2` 分支，并通过从目标方位减去第二个连杆的角度偏移来计算 `q1`。几何检查将工具和居中有效负载建模为磁盘。它通过将夹具中心投影到该段上、将投影夹紧到其端点并减去两个半径来计算每个直工具段的精确最小间隙。 IK 采样展示了对一个分支的影响。链接碰撞、关节限制、方向和计时需要在全臂模型中进行自己的检查。

```python
from math import acos, atan2, cos, hypot, sin

LINK_1, LINK_2 = 0.45, 0.35
START, GOAL = (0.35, 0.20), (0.75, 0.20)
FX, FY, FIXTURE_R = 0.55, 0.27, 0.03


def ik(x, y):
    cosine = (x*x + y*y - LINK_1**2 - LINK_2**2) / (2 * LINK_1 * LINK_2)
    q2 = acos(cosine)
    q1 = atan2(y, x) - atan2(LINK_2 * sin(q2), LINK_1 + LINK_2 * cos(q2))
    return q1, q2


def check(path, tool_radius):
    clearance = float("inf")
    for (x, y), (ex, ey) in zip(path, path[1:]):
        dx, dy = ex - x, ey - y
        length_sq = dx*dx + dy*dy
        t = ((FX - x) * dx + (FY - y) * dy) / length_sq if length_sq else 0
        t = min(1, max(0, t))
        gap = hypot(x + t*dx - FX, y + t*dy - FY) - FIXTURE_R - tool_radius
        clearance = min(clearance, gap)
        for step in range(21):
            px, py = x + dx*step/20, y + dy*step/20
            q1, q2 = ik(px, py)
            rx = LINK_1*cos(q1) + LINK_2*cos(q1 + q2)
            ry = LINK_1*sin(q1) + LINK_2*sin(q1 + q2)
            assert hypot(rx - px, ry - py) < 1e-9
    return clearance


straight = [START, GOAL]
detour = [START, (0.35, 0.12), (0.75, 0.12), GOAL]
for label, path, radius, feasible in [
    ("empty straight", straight, 0.015, True),
    ("loaded straight", straight, 0.050, False),
    ("loaded detour", detour, 0.050, True),
]:
    gap = check(path, radius)
    assert (gap > 0) == feasible
    print(f"{label}: minimum tool-fixture clearance {1000*gap:+.0f} mm")
```

预计分别为+25、-10 和+70 毫米。两条直线的中心线和 IK 样本是相同的。仅几何形状就改变了结论。在仿真器中，保存场景快照、目标位姿、首次拒绝的配置和碰撞对。对于运行时诊断，通过比较带时间戳的工具、关节和对象观测结果，分离位姿估计误差、规划器拒绝、控制器跟踪故障和对象滑动。报告每个阶段的成功、规划延迟、最小间隙和最终放置错误。在进行任何监督调试之前，测试可到达和不可到达的位姿、陈旧的观测结果以及故意阻止的撤退。桌面顶点将工作扩展为一个提供证据的实验。 [桌面顶石](/zh/notes/capstone-tabletop/)

## 练习

1. 抓取候选者将所携带的圆盘沿底座 +Y 向固定装置偏移 0.02 m，在整个传输过程中方向固定。预测并检查加载的直线间隙。

<details>
<summary>解决方案</summary>

承载的中心线现在位于 `y = 0.22`。缺口为`0.27 − 0.22 − 0.03 − 0.05 = −0.03 m`。对于此夹具，通过将夹具向下移动 0.02 m 以进行有效负载检查，同时保持 IK 不变，来模拟实验室中的偏移。旋转工具需要在每个位姿上应用附件变换。

</details>

2. 传输计划是模拟的，但提升后该块仍保留在托盘上。场景显示它已连接。哪些证据应该控制转变？你将如何测试它？

<details>
<summary>解决方案</summary>

一旦握力证据通过，将依恋视为对几何形状的预测。需要模拟接触和合理的手指分离，然后在短暂的验证提升过程中验证相对的工具到物体的变换。使用偏置手指注入抓握，无需获取块即可关闭。在授权转移之前，检查主管是否中止或协调场景。记录夹具结果和对象的实际状态以及场景更新。

</details>

## 总结

将接近、抓握、撤退和释放作为阶段进行规划，并观察完成条件。使用任务空间来表达工具约束和关节空间来检查手臂可以做什么。在有效负载改变机器人的几何形状后重新验证场景和定时运动。
