---
title: "移动机器人导航系统"
topic: "Planning and autonomy"
order: "051"
description: "连接全局路径、本地控制、定位和恢复，然后测试为什么同一路径可能需要不同的运动决策。"
prerequisites: "搜索和运动规划、坐标系和基本反馈。"
minutes: 50
---

## 在不断变化的走廊中遵循路线

室内差动驱动移动机器人有一条通往充电站的路线。有人推着一辆手推车穿过隔壁门口。作为意图声明，路线仍然有意义，但下一个速度命令必须考虑到小车。导航系统不断地关闭这个循环。它估计机器人的位置，更新它认为可以穿越的区域，计划去哪里，并跟踪进度。即使整个系统变得不一致，每个部分也可以返回合理的输出。

```text
Goal in map -> [global planner] -> path in map -----------+
                      ^                                   v
              global costmap                     [local controller]
                                                          |
Scan at t -> [transform at t] -> rolling local costmap ---+
                                                          |
Odom pose and twist -------------------------------------+
                                                          v
                                  body command v, yaw rate to base

The executive observes progress and can cancel or request a new path.
```

箭头显示数据依赖性。全球规划者找到了一条通往海湾的走廊。本地控制器使用短水平线来选择跟踪当前位姿的路径的运动。对于移动机器人，基本命令通常包含以 m/s 为单位的前进速度和以 rad/s 为单位的偏航角速度。基地自己的轮子反馈回路试图实现该命令。路径、身体命令和实际运动的证据是三个不同的信号。 [反馈控制](/zh/notes/pid-feedback/)

## 保持位姿和世界模型一致

<figure class="lesson-figure">
  <a href="/assets/figures/navigation-workflow.svg"><img src="/assets/figures/navigation-workflow.svg" width="640" height="430" loading="lazy" decoding="async" alt="全局规划器提供一条路线。本地控制器将该路线与标记扫描和里程计结合起来，以选择前进速度和偏航率。"></a>
  <figcaption>路线说的是去哪里。控制器仍然需要当前姿态和局部障碍物数据来决定现在是否以及如何移动。</figcaption>
</figure>

将变换链写为 `map → odom → base_link → laser`。里程计系统拥有 `odom → base_link`。车轮估计可能会漂移，但姿态应该不断变化。本地化可以通过发布 `map → odom` 来纠正这种漂移，因此地图框架位姿可以跳跃。这使得地图框架适合目标，而里程计框架对于平滑的本地反馈很有用。使用兼容的变换在局部框架中表达地图框架路径，并在大量修正后使计划假设无效。用于将小车放置在成本地图中的扫描需要在其采集时进行转换。在扫描上标记其传送时间可以产生与机器人一起移动的明显障碍物。 [REP-105 帧定义](https://raw.githubusercontent.com/ros-infrastructure/rep/master/rep-0105.rst) · [ROS 2 帧和时间](/zh/notes/ros2-frames-and-time/)

成本图离散化可遍历性。静态层可以对建筑物进行编码。观察层可以标记返回并使用清晰的传感器射线来移除陈旧的占用单元。未观测到的空间需要明确的策略。路线规划者在构建已知空间路线时可能会将其视为禁止。移动的本地窗口可以强调附近的新数据。足迹描述了其基座坐标系中的主体，包括突出部分。在候选位姿处，旋转和平移多边形，然后检查其覆盖的占用单元。圆盘近似更容易检查，并且可以阻止真正的矩形可以进行的转弯。障碍物周围的分级膨胀使规划者有理由选择走廊中间。检查每个插件在致命成本、未知成本和多边形检查方面的作用。这些选择决定了分级场和硬碰撞抑制如何相互作用。 [Nav2 Jazzy costmap 足迹源码](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_costmap_2d/src/costmap_2d_ros.cpp) · [Jazzy 通胀源码](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_costmap_2d/plugins/inflation_layer.cpp)

## 一起选择控制器和恢复策略

前瞻路径跟随器转向路径上前方的目标。短的前瞻对交叉跟踪错误反应灵敏。长命令可以使命令变得流畅，但可能会偷工减料。相反，推出控制器通过预测移动机器人在地平线上的运动并对跟踪努力、间隙和进度的轨迹进行评分来评估候选命令。检查速度和转向限制，并检查沿候选运动的碰撞。如果没有可行的命令，请区分临时阻塞和持续故障。进度检查可以询问移动机器人是否在时间窗口内移动了最小距离。目标检查询问位置和航向是否在其容差范围内。设置进度检查，以便合理的慢速或仅旋转操作有机会完成。

ROS 2 上的 Nav2 Jazzy 通过带有插件的规划器和控制器服务器以及协调操作的行为树导航器来表达这些角色。其 Jazzy Bringup 示例在 `odom` 中使用滚动本地成本图，在 `map` 中使用全局成本图。提供的一棵树在符合条件的规划器或控制器错误后尝试上下文成本图清除，并且具有有限的重试和恢复操作。阅读你部署的版本的实际树和参数。在小车仍然存在的模拟中，清除观察图层可能会暂时隐藏小车。在再次考虑运动之前，需要进行新的传感和有效的足迹检查。在监督调试中允许任何运动恢复之前分析扫过的区域。 [Nav2 Jazzy 导航服务器](https://docs.nav2.org/jazzy/getting_started/navigation_concepts/navigation_servers/) · [Jazzy 启动参数](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_bringup/params/nav2_params.yaml) · [Jazzy 重新规划和恢复树](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml)

## 实验室：在同一路径上回放本地决策

保持全局路径固定，并使用静止的推车对一条直线段进行建模。输入间隙是传感器采集时距移动机器人前部足迹的自由距离，以米为单位。假设制动开始前的速度上限为 `v`，恒定制动减速度的下限为 `a > 0`，剩余距离储备为 `m`。建模的间隙预算为 `d = v(age + lag) + v²/(2a) + m`。第一个术语涵盖捕获和制动之间的行程。第二个来自恒定减速运动学。在这里，管理人员可以继续跟踪或请求停止。太晚提出停止请求仍可能超出剩余距离。

另存为 `replay_nav.py` 并运行 `python replay_nav.py`。输入时间是合成共享时钟上的秒。年龄限制和距离是实验室规定的。

```python
from math import isclose

SPEED, BRAKE, LAG, RESERVE = 0.40, 0.50, 0.05, 0.08
MAX_AGE = 0.30


def evaluate(clearance, age):
    if clearance is None or not 0 <= age <= MAX_AGE:
        return "stop: missing or stale", None
    budget = SPEED * (age + LAG) + SPEED**2 / (2 * BRAKE) + RESERVE
    return ("track" if clearance > budget else "stop: blocked"), budget


cases = [
    ("fresh", 0.30, 0.05, "track", 0.28),
    ("delayed", 0.30, 0.25, "stop: blocked", 0.36),
    ("closer", 0.24, 0.05, "stop: blocked", 0.28),
    ("expired", 0.60, 0.40, "stop: missing or stale", None),
    ("dropout", None, 0.05, "stop: missing or stale", None),
]
for label, clearance, age, expected, expected_budget in cases:
    decision, budget = evaluate(clearance, age)
    assert decision == expected
    if expected_budget is None:
        assert budget is None
    else:
        assert isclose(budget, expected_budget)
    distance = "-" if budget is None else f"{budget:.2f} m"
    print(label, decision, distance)
```

新案例的预算为 0.28 m。延迟相同的观察会将预算提高到 0.36 m 并触发停止请求。即使报告的许可范围更大，过期的案件也要求停止。这是一个决策边界的 CPU 模型。曲线、接近的障碍物、执行器故障和未知空间需要额外的证据。为了进行更忠实的模拟，请在一条时间线上重放带有时间戳的变换和绘图间隙、命令和测量的停止距离的移动障碍物。

## 调整前测试边界

从一条空地图路线开始，然后从固定位姿重复该路线。测量完成率、路径长度、交叉航迹误差、最终偏航误差、最小模拟间隙和观察到命令延迟。保持地图和机器人版本固定。然后在已知时间插入一种干扰，例如走廊堵塞、定位跳跃、冻结扫描或丢失变换。检查哪个子系统首先报告故障、命令是否在模拟期限内停止、移动机器人是否在模拟包络内停止以及重试是否有限制。使用相同的输入顺序回放第一次失败。比较成本图更新时的扫描年龄、控制器查询的姿态和足迹以及调整增益或膨胀之前的实际基本响应。 [ROS 2 袋及测试](/zh/notes/ros2-bags-and-testing/)

## 练习

1. 日志报告 0.30 m 的间隙和 0.25 s 的寿命。计算恰好满足建模预算的速度限制。为什么此时改变速度设定值证据不足？

<details>
<summary>解决方案</summary>

求解 `v² + 0.30v − 0.22 = 0` 的正根，约为 0.342 m/s。实验室中的跟踪需要严格较小的速度限制。设定点更改后，移动机器人可能仍以其先前的速度行驶。在评估立即停止时，使用测量的速度和延迟间隔的保守界限。

</details>

2. 每当定位在同一架子附近进行较大修正时，移动机器人就会停止前进。设计一个回放来区分真正的障碍物和帧错误。

<details>
<summary>解决方案</summary>

记录扫描标记、动态变换、位姿估计和被拒绝的控制器候选者。在 `odom` 中叠加转换后的扫描和扫描足迹。将使用采集时间转换的运行与使用最新转换的运行进行比较，同时保持原始扫描和命令历史记录固定。检查校正是否与移动的地图框路线、错位的扫描或两次回放中一致占据的区域一致。

</details>

## 总结

全局规划选择一条路线。本地控制将路线和当前观测结果转化为可行的命令。时间、框架一致性、足迹几何形状和测量的进度决定何时继续、停止或重新计划。在模拟中测试闭环行为之前，通过确定性重放验证这些边界。
