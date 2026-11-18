---
title: When a robot should learn and what it should learn
topic: Robot learning
order: "090"
description: Compare scripted control, imitation, and reinforcement learning with the same task contract and baseline.
prerequisites: Feedback, basic estimation, and introductory machine learning.
minutes: 55
---

## Make learning answer a specific question

A robot can use a learned detector and still drive with a classical controller. It can also use exact state from a simulator and learn a control policy. These are different engineering decisions. Ask which input–output mapping is too expensive to specify, what data you can obtain, what errors are recoverable, and how you will compare against a simpler implementation.

For a tabletop task, begin with a scripted sequence that succeeds on known resets. If it fails even on the simplest scene, adding a policy hides a baseline defect. If it works on clean poses but struggles under visual variation, a detector may solve the difficult part without replacing the whole controller.

## Use a shared task contract

```text
 observation at t ──▶ policy ──▶ bounded action at t
      ▲                                    │
      │                                    ▼
 observation at t+1 ◀── environment transition
                            ├─ outcome / termination
                            └─ reward (if the task defines one)
```

State might contain the object's pose, friction regime, or contact history. The observation may contain only a cropped image and joint angles. If two latent states look identical and require different actions, no memoryless policy can discriminate them from that observation alone. A history, a new sensor, or a safer fallback can make the problem better posed.

| Method | Supervision | Advantages | Failure to test |
| --- | --- | --- | --- |
| Scripted feedback | Programmer-specified model and rules | Clear baseline; often cheap to test and diagnose | State estimation or contact assumptions fail |
| Behavior cloning | Demonstrated observations and actions | Direct supervised objective when competent demos are available | Small errors move the policy outside the demonstrations |
| Reinforcement learning | Environment interaction and reward | Can discover behavior not in a demonstration set | Exploits proxy rewards, learns simulator shortcuts, or requires many trials |
| Hybrid | Rules or planning plus a learned component | Limit the role of learning and preserve known invariants | Coupling hides where the first error entered |

Reinforcement learning may also use offline data; the table describes common starting workflows, not rigid definitions. An episode defines reset and ending conditions. A reward is a signal the learner sees, not proof that behavior is useful. A policy can obtain a high proxy reward while missing the task.

## Lab: catch a reward that teaches the wrong behavior

This is a one-step environment, not an RL training implementation. Each candidate picks a destination from 0 through 10. Target is 6. A badly designed rubric rewards speed without enough cost for overshoot. Run the code and compare the winner under each reward with the independently defined task success.

```python
TARGET = 6
DESTINATIONS = range(11)


def succeeds(destination):
    return abs(destination - TARGET) <= 1


def flawed_reward(destination):
    return destination - 0.5 * abs(destination - TARGET)


def task_reward(destination):
    return 2.0 * succeeds(destination) - 0.1 * abs(destination - TARGET)


for label, score in (("flawed", flawed_reward), ("revised", task_reward)):
    winner = max(DESTINATIONS, key=score)
    print(label, "destination", winner, "reward", score(winner), "success", succeeds(winner))

assert max(DESTINATIONS, key=flawed_reward) == 10
assert max(DESTINATIONS, key=task_reward) == 6
```

The first objective encourages larger positive destinations even after the target. At position 10, its reward is 8, higher than 6 at the target. An optimizer is not at fault for finding that solution. In the revised reward, task success matters more and exact position breaks the tie. In a real experiment, add tests against unsafe routes, timeout, repeated progress credit, and unobservable labels instead of trusting this scalar recipe.

Change only the overshoot penalty in the flawed reward. Above 6, the score increases with destination if the coefficient is below 1, is flat when it equals 1, and decreases above 1. At equality, multiple destinations tie for best score, and an implementation's tie-break may hide the failure. Inspect all maximizers, not only one.

## Put the learning work in a development order

1. Write the allowed observations, action space, control interval, reset scope, termination, success criterion, and known unsafe conditions. Use the same observation contract for all candidate policies unless the extra sensor is the experiment.
2. Run a random or constant command baseline and an interpretable expert. Report failure categories. A demo that films only the successful trials is not a benchmark.
3. For imitation, audit demonstration timing, hold out whole trajectories or sessions, and fit normalization only on training data. For RL, inspect reward components and run a stress test where the proxy and actual success can disagree.
4. Overfit a tiny batch to check the training path, then evaluate closed-loop resets with fixed trial counts and a comparison budget. Record inference timing; a policy can be correct but too slow.
5. Examine the earliest deviation on the same reset. Verify command scaling, ordering, stale inputs, and whether the next observation is outside the training distribution before changing architecture.

See [the LeRobot data lecture](/notes/lerobot-data/) for an executable starting workflow and [the capstone CPU experiment](/notes/capstone-tabletop/#cpu-mini-project-learn-why-a-replay-score-is-not-a-rollout-score) for a direct comparison of offline and rollout scores. [Spinning Up's RL concepts](https://spinningup.openai.com/en/latest/spinningup/rl_intro.html) describes policy, trajectory, return, and reward terminology.

## Exercises

A policy follows a visual target in simulation but the goal location is accidentally present in a debug tensor that has no real sensor equivalent. What has been demonstrated?

<details>
<summary>Check the observation contract</summary>
<p>An oracle baseline for the simulated task. Remove the extra tensor, build a valid estimate, or clearly describe a different intended sensor. Retrain or reevaluate under the actual observation contract.</p>
</details>

Your imitation policy rarely recovers after a missed push. It has very low held-out action error on expert data. What experiment distinguishes lack of recovery data from a wrong output scale?

<details>
<summary>Check the first divergence</summary>
<p>Drive a known target through the saved postprocessor and verify action semantics in the simulator first. Then compare matched rollouts and place the agent in a bounded simulated recovery state to see whether it generates a corrective action. If the representation passes and correction is missing only off the demonstrated trajectory, investigate coverage.</p>
</details>

## What to carry forward

Choose learning when its data and evaluation answer the same engineering question. Preserve a simpler baseline and treat rewards, exact simulator state, and logged trajectories as evidence with defined limits.
