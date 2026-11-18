"""Track a grid route with a kinematic point rover and an encoder scale error."""

import argparse
import math

from rover_project import GOAL, NEW_OBSTACLE, START, STATIC_WALL, plan


CELL_SIZE = 0.4
DT = 0.05
TRACK = 0.30
RADIUS = 0.05
MAX_WHEEL_RATE = 5.0
ARRIVAL = 0.02
MAX_TICKS = 1_800


def center(cell):
    return tuple((value + 0.5) * CELL_SIZE for value in cell)


def wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def follow(pose, target):
    pos_x, pos_y, heading = pose
    delta_x, delta_y = target[0] - pos_x, target[1] - pos_y
    angle_error = wrap(math.atan2(delta_y, delta_x) - heading)
    if abs(angle_error) > 0.02:
        return 0.0, max(-1.0, min(1.0, 4.0 * angle_error))
    return min(0.20, 2.0 * math.hypot(delta_x, delta_y)), 0.0


def to_wheels(speed, yaw_rate):
    left = (speed - TRACK * yaw_rate / 2.0) / RADIUS
    right = (speed + TRACK * yaw_rate / 2.0) / RADIUS
    scale = max(1.0, abs(left) / MAX_WHEEL_RATE, abs(right) / MAX_WHEEL_RATE)
    return left / scale, right / scale


def advance(pose, wheels):
    pos_x, pos_y, heading = pose
    left, right = wheels
    travel = DT * RADIUS * (left + right) / 2.0
    turn = DT * RADIUS * (right - left) / TRACK
    midpoint_heading = heading + turn / 2.0
    return (pos_x + travel * math.cos(midpoint_heading),
            pos_y + travel * math.sin(midpoint_heading), wrap(heading + turn))


def clearance(pose, walls):
    pos_x, pos_y = pose[:2]
    return min(
        math.hypot(
            max(col * CELL_SIZE - pos_x, 0.0, pos_x - (col + 1) * CELL_SIZE),
            max(row * CELL_SIZE - pos_y, 0.0, pos_y - (row + 1) * CELL_SIZE),
        )
        for col, row in walls
    )


def run(encoder_scale):
    walls = STATIC_WALL | {NEW_OBSTACLE}
    targets = [center(cell) for cell in plan(START, GOAL, walls)[1:]]
    truth = estimate = (*center(START), 0.0)
    minimum_clearance = clearance(truth, walls)
    waypoint = tick = 0
    for tick in range(1, MAX_TICKS + 1):
        if waypoint == len(targets):
            break
        target = targets[waypoint]
        if math.dist(estimate[:2], target) <= ARRIVAL:
            waypoint += 1
            continue
        wheels = to_wheels(*follow(estimate, target))
        assert max(map(abs, wheels)) <= MAX_WHEEL_RATE + 1e-9
        truth = advance(truth, wheels)
        estimate = advance(estimate, tuple(rate * encoder_scale for rate in wheels))
        minimum_clearance = min(minimum_clearance, clearance(truth, walls))
        if minimum_clearance == 0.0:
            break
    residual = math.dist(truth[:2], center(GOAL))
    drift = math.dist(truth[:2], estimate[:2])
    if minimum_clearance == 0.0:
        outcome = "sampled_collision"
    elif waypoint != len(targets):
        outcome = "deadline"
    elif residual > 0.08:
        outcome = "estimated_arrival_only"
    else:
        outcome = "reached_goal"
    return outcome, tick, residual, drift, minimum_clearance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--encoder-scale", type=float, default=1.0)
    args = parser.parse_args()
    if not math.isfinite(args.encoder_scale) or not 0.8 <= args.encoder_scale <= 1.2:
        parser.error("encoder scale must be between 0.8 and 1.2")
    outcome, ticks, residual, drift, nearest = run(args.encoder_scale)
    print(f"{outcome}: ticks={ticks}, true goal error={residual:.3f} m, "
          f"pose drift={drift:.3f} m, sampled clearance={nearest:.3f} m")


if __name__ == "__main__":
    main()
