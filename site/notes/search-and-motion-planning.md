---
title: "Search and motion planning"
topic: "Planning and autonomy"
order: "050"
description: "Turn robot geometry and motion constraints into a search problem, then measure what changes when a path has to fit a real footprint."
prerequisites: "Python heaps and dictionaries, plus the coordinate frames chapter."
minutes: 50
---

## Plan for the space the robot occupies

An indoor rover has to travel from a bench to a charging bay. The shortest line on the map passes through a narrow opening. The first question is whether the rover fits there. The second is whether it can reach that opening at a heading that lets it pass, then follow the route at a feasible speed. A planning problem should identify which of those questions it answers and what a downstream component will have to check.

A **configuration** is a set of coordinates that determines the shape and pose of the modeled robot. A planar rover configuration is `q = (x, y, θ)` in the map frame, with positions in meters and yaw in radians. A fixed tabletop arm's configuration typically consists of its joint coordinates. For a circular rover on a flat floor with only static obstacles, the collision question can ignore yaw. A rectangular rover may fit at one yaw and strike a corner at another. Modeling it as a disk that encloses the full footprint is conservative and can rule out feasible passages.

The set of all configurations is **configuration space**. Mark a configuration as forbidden if the robot at that pose intersects an obstacle. For a disk of radius `r`, each obstacle can be expanded by `r` in workspace and the rover's center treated as a point. An exact disk against an occupied square requires distance to the square, including its edges. A threshold on distance to the cell center alone can miss collisions. A clearance margin can enlarge `r` further to account for bounded model and tracking error.

```text
Top view, point search        Same opening, footprint-aware search
      #                                 ###
 S -> . -> G  one free row     S        ###      G
      #                                 ###

 # forbidden     . free opening     S start     G goal
```

Each sketch shows a slice through the same wall. In the second sketch, expansion grows the blocked region into the opening, so the center of the rover cannot pass in this discrete model. A wider opening elsewhere can still offer a route.

## Choose states, edges, and a cost

A grid makes an implicit graph. Nodes are free cell centers. Edges in this lab are one-cell moves along an axis, with cost equal to one grid step. A* prioritizes `f(n) = g(n) + h(n)`. The first term is the best cost found from the start. The second estimates the remaining cost. On this four-connected grid, Manhattan distance is a lower bound because each move reduces the sum of the two coordinate differences by at most one. It is also consistent because its drop along any edge is at most that edge's cost. With this cost and heuristic, the first goal removed from the heap has optimal cost on this graph. Multiplying both terms by cell size expresses cost in meters. Setting `h = 0` gives Dijkstra's algorithm and a useful test oracle. With a nonnegative clearance penalty, unpenalized distance remains a lower bound.

Edge validity is a separate contract. Two valid states can have an obstacle between them. A diagonal between free cells that touch at a corner can cut between occupied neighbors. A shortcut introduced by smoothing needs a fresh collision check, even when both endpoints came from a valid plan. An exact swept-volume query checks the region covered throughout the motion. Discrete interpolation offers a cheaper check, but widely spaced samples can miss thin obstacles or a rotating protrusion. The Open Motion Planning Library exposes separate state and motion validity interfaces, and its documentation discusses that sampling tradeoff. [OMPL state validity documentation](https://ompl.kavrakilab.org/stateValidation.html)

For a differential-drive rover with body forward speed `v` and yaw rate `ω`, the planar velocity model is `ẋ = v cos θ`, `ẏ = v sin θ`, `θ̇ = ω`. Instantaneous body-frame sideways velocity is zero. A circular model may permit a turn in place at a cell center, but graph edges alone specify neither heading nor acceleration. For motions that depend on heading, search over position and heading with edges that represent feasible turns or arcs. Include limits and timings when converting a path to a trajectory. See [Coordinate frames](/notes/coordinate-frames/) for how a body-frame direction rotates into the map.

## Lab: compare a point route with a footprint route

Save the code as `grid.py` and run `python grid.py`. The grid is 13 by 13 with 0.10 m cells. Indices are `(x, y)`, increasing right and up, so index `(i, j)` represents center `((i + 0.5)s, (j + 0.5)s)` for cell size `s`. Column 6 is a wall with a one-cell gap in row 3 and a three-cell gap in rows 7–9. The rover has an effective radius of 0.06 m. A conservative rasterization blocks an entire candidate square if any point in it lies within the radius of an occupied square. This can lose viable routes. Its advantage here is that a cardinal center-to-center edge stays within the union of two validated cells.

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

Expect lengths of 0.80 m via `(6, 3)` and 1.80 m via `(6, 8)`. The two search algorithms should agree on cost within each model. The expansion counter includes the goal and excludes stale heap entries. Counts depend on tie breaking. On larger maps, log search latency and expansions separately from map construction. Record grid origin, resolution, footprint, and map revision alongside the path. If a map change breaks a route, plot a rejected edge and its first collision before changing heuristic weights.

## When to change the method

A finer grid can recover narrow passages, at the cost of more cells and collision checks. A heading lattice can preserve rover constraints and still let you inspect and reproduce the graph. Sampling methods such as RRT grow a tree by drawing configurations and attempting local connections. They can be useful in a high-dimensional arm space whose full grid would be enormous. Narrow passages and tight time budgets may give them few useful samples. Benchmark multiple seeds and validate every returned segment. Trajectory optimization adjusts a candidate to minimize objectives such as length, curvature, or control effort under constraints. It can refine a good initial route and may settle in a local minimum or fail to find a feasible one. Validate the optimized result independently, including the clearance between its knots.

## Exercises

1. A team moves the goal to `(7, 3)` and reports that the wider passage still fails. Predict and reproduce the failure, then try `(8, 3)`.

<details>
<summary>Solution</summary>

With the disk model, the cell at `(7, 3)` touches the occupied wall cells at `(6, 2)` and `(6, 4)` at corners. Its square-to-square distance to them is zero, so `search(blocked_cells(0.06), goal=(7, 3))` returns `(None, 0)` before search. Moving one cell farther from the wall puts the goal in free space. Log blocked start or goal separately from exhausting the search frontier.

</details>

2. A path postprocessor proposes a straight shortcut between the start and goal for the disk. Build a regression check specific to that shortcut and explain its scope.

<details>
<summary>Solution</summary>

Here the segment lies along the centers of row 3. Check every cell from `(2, 3)` through `(10, 3)` against `blocked_cells(0.06)`. Cell `(6, 3)` fails, so retain the detour. For arbitrary endpoints, enumerate every touched cell conservatively or use a continuous geometry check. A heading-dependent footprint also needs a motion model for orientation along the edge.

</details>

## Summary

Optimal search only optimizes the graph you supply. Choose a configuration space and a collision model that represent the robot, validate edges as well as states, and keep graph cost distinct from execution time. The next lecture puts this search inside a feedback loop that must react when the map or rover pose changes. [Navigation systems](/notes/navigation-systems/)
