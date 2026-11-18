---
title: "搜索与运动规划"
topic: "Planning and autonomy"
order: "050"
description: "将机器人几何和运动约束转化为搜索问题，然后测量当路径必须适合真实足迹时发生的变化。"
prerequisites: "Python 堆和字典，以及坐标系章节。"
minutes: 50
---

## 规划机器人占用的空间

室内移动机器人必须从长凳移动到充电站。地图上最短的线穿过一个狭窄的开口。第一个问题是移动机器人是否适合那里。第二个问题是它是否能够以允许其通过的航向到达该开口，然后以可行的速度沿着路线行驶。规划问题应该确定它回答哪些问题以及下游组件必须检查哪些问题。

配置是确定建模机器人的形状和位姿的一组坐标。平面移动机器人配置在地图框中为 `q = (x, y, θ)`，位置以米为单位，偏航以弧度为单位。固定桌面臂的配置通常由其关节坐标组成。对于平坦地面上仅有静态障碍物的圆形移动机器人，碰撞问题可以忽略偏航。矩形移动机器人可能会在一个偏航处安装，并在另一个偏航处撞到拐角。将其建模为包含整个足迹的圆盘是保守的，并且可以排除可行的通道。

所有配置的集合就是配置空间。如果处于该位姿的机器人与障碍物相交，则将配置标记为禁止。对于半径为`r`的圆盘，每个障碍物都可以在工作空间中通过`r`扩展，并将移动机器人的中心视为一个点。一个精确的圆盘对着一个占据的方格需要与该方格有一定的距离，包括它的边缘。仅距细胞中心距离的阈值就可能会错过碰撞。间隙裕度可以进一步放大 `r`，以考虑有界模型和跟踪误差。

```text
Top view, point search        Same opening, footprint-aware search
      #                                 ###
 S -> . -> G  one free row     S        ###      G
      #                                 ###

 # forbidden     . free opening     S start     G goal
```

每个草图都显示了同一堵墙的一个切片。在第二个草图中，扩展将阻塞区域增长到开口中，因此移动机器人的中心无法通过此离散模型。其他地方更广泛的开放仍然可以提供一条路线。

## 选择状态、边缘和成本

网格构成隐式图。节点是自由的单元中心。本实验中的边缘是沿轴的一个栅格移动，其成本等于一个网格步长。 A* 优先考虑 `f(n) = g(n) + h(n)`。第一项是从一开始就找到的最佳成本。第二个估计剩余成本。在这个四连通网格上，曼哈顿距离是一个下界，因为每次移动都会将两个坐标差的总和最多减少 1。它也是一致的，因为它沿任何边的下降最多是该边的成本。通过此成本和启发式，从堆中删除的第一个目标在此图上具有最佳成本。将这两项乘以像元大小即可表示成本（以米为单位）。设置 `h = 0` 可以提供 Dijkstra 算法和有用的测试预言机。在非负清除惩罚的情况下，未惩罚距离仍然是下限。

边缘有效性是一个单独的合同。两个有效状态之间可能存在障碍。在角落接触的空闲单元之间的对角线可以在占用的邻居之间进行切割。平滑引入的快捷方式需要新的碰撞检查，即使两个端点都来自有效的计划。精确的扫描体积查询检查整个运动覆盖的区域。离散插值提供了更便宜的检查，但宽间隔的样本可能会错过薄障碍物或旋转突出物。开放运动规划库公开了单独的状态和运动有效性接口，其文档讨论了采样权衡。 [OMPL 状态有效性文档](https://ompl.kavrakilab.org/stateValidation.html)

对于主体前进速度为 `v`、偏航角速度为 `ω` 的差动驱动移动机器人，平面速度模型为 `ẋ = v cos θ`、`ẏ = v sin θ`、`θ̇ = ω`。瞬时车身框架侧向速度为零。圆形模型可能允许在单元中心适当转弯，但图形边缘单独指定既不指定航向也不指定加速度。对于依赖于航向的运动，请使用表示可行转弯或弧线的边缘搜索位置和航向。将路径转换为轨迹时包括限制和时间。有关主体坐标系方向如何旋转到地图中的信息，请参阅[坐标系](/zh/notes/coordinate-frames/)。

## 实验室：比较点路线与足迹路线

将代码保存为 `grid.py` 并运行 `python grid.py`。网格尺寸为 13 x 13，栅格大小为 0.10 m。 Indices are `(x, y)`, increasing right and up, so index `(i, j)` represents center `((i + 0.5)s, (j + 0.5)s)` for cell size `s`.第 6 列是一堵墙，第 3 行有一个单元间隙，第 7-9 行有三个单元间隙。移动机器人的有效半径为0.06 m。如果候选方格中的任何点位于占用方格的半径内，则保守光栅化会阻塞整个候选方格。这可能会失去可行的路线。它在这里的优点是基本中心到中心边缘保留在两个经过验证的栅格的并集内。

```python
from heapq import heappop, heappush
from math import hypot, inf

N, CELL = 13, 0.10
START, GOAL = (2, 3), (10, 3)
WALL = {(6, y) for y in range(N) if y not in (3, 7, 8, 9)}
STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def blocked_cells(radius):
    if radius == 0:
        return WALL.copy()
    blocked = set()
    for x in range(N):
        for y in range(N):
            boundary = CELL * min(x, y, N - 1 - x, N - 1 - y)
            if boundary <= radius:
                blocked.add((x, y))
            for ox, oy in WALL:
                dx = CELL * max(0, abs(x - ox) - 1)
                dy = CELL * max(0, abs(y - oy) - 1)
                if hypot(dx, dy) <= radius:
                    blocked.add((x, y))
                    break
    return blocked


def search(blocked, goal=GOAL, use_heuristic=True):
    def estimate(cell):
        return sum(abs(a - b) for a, b in zip(cell, goal)) if use_heuristic else 0

    if START in blocked or goal in blocked:
        return None, 0
    queue = [(estimate(START), 0, START)]
    best, parent = {START: 0}, {}
    expanded = 0
    while queue:
        _, cost, cell = heappop(queue)
        if cost != best[cell]:
            continue
        expanded += 1
        if cell == goal:
            path = [cell]
            while cell != START:
                cell = parent[cell]
                path.append(cell)
            return path[::-1], expanded
        x, y = cell
        for dx, dy in STEPS:
            nxt = x + dx, y + dy
            nx, ny = nxt
            if 0 <= nx < N and 0 <= ny < N and nxt not in blocked:
                if cost + 1 < best.get(nxt, inf):
                    best[nxt], parent[nxt] = cost + 1, cell
                    heappush(queue, (cost + 1 + estimate(nxt), cost + 1, nxt))
    return None, expanded


for radius, expected in [(0.0, 8), (0.06, 18)]:
    blocked = blocked_cells(radius)
    path, expanded = search(blocked)
    baseline, baseline_expanded = search(blocked, use_heuristic=False)
    assert len(path) - 1 == len(baseline) - 1 == expected
    assert all(cell not in blocked for cell in path)
    assert all((b[0] - a[0], b[1] - a[1]) in STEPS for a, b in zip(path, path[1:]))
    crossing = next(cell for cell in path if cell[0] == 6)
    print(f"{radius:.2f} m: {expected * CELL:.2f} m via {crossing}; "
          f"expanded A*/Dijkstra = {expanded}/{baseline_expanded}")
```

通过 `(6, 3)` 预计长度为 0.80 m，通过 `(6, 8)` 预计长度为 1.80 m。 The two search algorithms should agree on cost within each model.扩展计数器包括目标并排除陈旧的堆条目。计数取决于决胜局。 On larger maps, log search latency and expansions separately from map construction.沿着路径记录网格原点、分辨率、足迹和地图修订。 If a map change breaks a route, plot a rejected edge and its first collision before changing heuristic weights.

## 何时改变方法

更精细的网格可以恢复狭窄的通道，但代价是更多的单元和碰撞检查。 A heading lattice can preserve rover constraints and still let you inspect and reproduce the graph. RRT 等采样方法通过绘制配置并尝试本地连接来生长树。 They can be useful in a high-dimensional arm space whose full grid would be enormous.狭窄的段落和紧张的时间预算可能会给他们带来很少的有用样本。 Benchmark multiple seeds and validate every returned segment.轨迹优化调整候选对象，以最大限度地减少约束下的目标，例如长度、曲率或控制工作。 It can refine a good initial route and may settle in a local minimum or fail to find a feasible one.独立验证优化结果，包括其结之间的间隙。

## 练习

1. 一个团队将目标移至 `(7, 3)`，并报告更广泛的通道仍然失败。预测并重现故障，然后尝试 `(8, 3)`。

<details>
<summary>解决方案</summary>

对于圆盘模型，`(7, 3)` 处的单元接触角落处 `(6, 2)` 和 `(6, 4)` 处占用的壁单元。它与它们的平方距离为零，因此 `search(blocked_cells(0.06), goal=(7, 3))` 在搜索之前返回 `(None, 0)`。将一个栅格移离墙壁更远，将目标置于自由空间中。记录受阻的开始或目标，与耗尽搜索边界分开。

</details>

2. 路径后处理器建议在磁盘的起点和目标之间建立一条直接的快捷方式。构建特定于该快捷方式的回归检查并解释其范围。

<details>
<summary>解决方案</summary>

这里，该段位于第 3 行的中心。对照 `blocked_cells(0.06)` 检查从 `(2, 3)` 到 `(10, 3)` 的每个栅格。栅格 `(6, 3)` 失败，因此保留绕行。对于任意端点，保守地枚举每个触摸的栅格或使用连续的几何检查。与航向相关的足迹还需要一个用于沿边缘定向的运动模型。

</details>

## 总结

最佳搜索仅优化你提供的图表。选择代表机器人的配置空间和碰撞模型，验证边缘和状态，并使图形成本与执行时间不同。下一讲将这种搜索置于反馈循环中，当地图或移动机器人姿态发生变化时，反馈循环必须做出反应。 [导航系统](/zh/notes/navigation-systems/)
