"""Simulate a point rover on a grid, including bounded replanning."""

import argparse
from collections import deque


WIDTH, HEIGHT = 8, 6
START, GOAL = (0, 2), (7, 2)
STATIC_WALL = {(3, row) for row in (0, 1, 3, 4)}
NEW_OBSTACLE = (3, 2)
DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1))


def neighbors(cell):
    col, row = cell
    for delta_col, delta_row in DIRECTIONS:
        next_col, next_row = col + delta_col, row + delta_row
        if 0 <= next_col < WIDTH and 0 <= next_row < HEIGHT:
            yield next_col, next_row


def plan(start, goal, walls):
    if start in walls or goal in walls:
        return []
    frontier = deque([start])
    predecessors = {start: None}
    while frontier:
        cell = frontier.popleft()
        if cell == goal:
            path = []
            while cell is not None:
                path.append(cell)
                cell = predecessors[cell]
            return path[::-1]
        for candidate in neighbors(cell):
            if candidate not in walls and candidate not in predecessors:
                predecessors[candidate] = cell
                frontier.append(candidate)
    return []


def run(scenario, budget=20):
    position = START
    walls = set(STATIC_WALL)
    commands = 0
    trace = []
    for tick in range(budget + 1):
        if position == GOAL:
            return "reached_goal", commands, trace
        if tick == budget:
            break
        if tick >= 2 and scenario in {"blocked", "sealed"}:
            walls.add(NEW_OBSTACLE)
        if tick >= 2 and scenario == "sealed":
            walls.add((3, 5))
        if tick >= 2 and scenario == "stale":
            return "stale_observation", commands, trace
        path = plan(position, GOAL, walls)
        if not path:
            return "no_route", commands, trace
        requested = path[1]
        assert requested in neighbors(position) and requested not in walls
        trace.append((tick, position, requested, len(path) - 1))
        position = requested
        commands += 1
    return "deadline", commands, trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("baseline", "blocked", "sealed", "stale"), default="baseline")
    parser.add_argument("--budget", type=int, default=20)
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()
    if args.budget < 0:
        parser.error("--budget must be nonnegative")
    outcome, commands, trace = run(args.scenario, args.budget)
    if args.trace:
        for tick, observation, command, remaining in trace:
            print(f"tick={tick:02} observation={observation} target={command} path_steps={remaining}")
    print(f"{args.scenario}: {outcome}; movement commands={commands}")


if __name__ == "__main__":
    main()
