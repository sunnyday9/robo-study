"""Compare offline error and rollout success in a synthetic one-axis task."""

from statistics import mean


TARGET = 1.0
LIMIT = 0.25
DISTURBANCE = 0.08
TOLERANCE = 0.03
HORIZON = 16
TRAIN_RESETS = (0.0, 0.1, 0.2)
TEST_RESETS = (0.05, 0.15, 0.25)


def bounded(command):
    return max(-LIMIT, min(command, LIMIT))


def expert(position):
    return bounded(TARGET - position + DISTURBANCE)


def step(position, command):
    return position + bounded(command) - DISTURBANCE


def episode(reset_position, policy):
    position = reset_position
    rows = []
    for index in range(HORIZON):
        command = policy(index, position)
        rows.append((index, position, command))
        position = step(position, command)
    return rows, position


def fit_open_loop(trajectories):
    actions = [mean(row[2] for row in tick) for tick in zip(*trajectories)]
    return lambda index, _position: actions[index]


def fit_feedback(trajectories):
    examples = [(position, command) for trajectory in trajectories for _, position, command in trajectory]
    biases = [command - (TARGET - position) for position, command in examples if abs(command) < LIMIT]
    bias = mean(biases)
    return lambda _index, position: bounded(TARGET - position + bias)


def evaluate(policy, demonstrations):
    errors = [
        mean(abs(policy(index, position) - expert_command) for index, position, expert_command in rows)
        for rows in demonstrations
    ]
    terminal_positions = [episode(reset, policy)[1] for reset in TEST_RESETS]
    count = sum(abs(position - TARGET) <= TOLERANCE for position in terminal_positions)
    return mean(errors), count, terminal_positions


def demonstrations(resets):
    return [episode(reset, lambda _index, position: expert(position))[0] for reset in resets]


def main():
    training = demonstrations(TRAIN_RESETS)
    held_out = demonstrations(TEST_RESETS)
    for name, policy in (("time-only", fit_open_loop(training)), ("feedback", fit_feedback(training))):
        error, count, positions = evaluate(policy, held_out)
        readings = ", ".join(f"{position:.3f}" for position in positions)
        print(f"{name}: offline MAE={error:.4f}, rollout success={count}/{len(TEST_RESETS)}, "
              f"terminal positions=[{readings}]")


if __name__ == "__main__":
    main()
