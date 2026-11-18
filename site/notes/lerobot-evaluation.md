---
title: Evaluate an imitation policy
topic: LeRobot
order: "33"
description: Verify the data contract and measure closed-loop behavior across reproducible simulator resets.
prerequisites: An ACT checkpoint and the PushT environment
minutes: 45
---

## Verify the policy–environment contract

A simulator accepts whatever action its controller defines. Two arrays of the same shape can encode incompatible quantities. Verify a known observation and a known action before evaluating success. The lab uses LeRobot’s documented PushT integration. [Tagged PushT config](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/envs/configs.py) · [PushT observation and action spaces](https://pypi.org/project/gym-pusht/0.1.6/)

| Boundary | Check for this checkpoint |
| --- | --- |
| Simulator → observation | `pixels` becomes `observation.image`, with RGB input at 96 × 96. Confirm channel order and scaling to `[0, 1]` before policy normalization. `agent_pos` becomes `observation.state` in x, y order. |
| Policy → simulator | The saved postprocessor returns an absolute x, y target in simulator units. The simulator’s accepted range is `[0, 512]` per axis. Check bounds, units and direction with a known horizontal target, and count out-of-range predictions. |
| Timing and reset | One command each 0.1 seconds of simulated time. The ACT checkpoint consumes four queued actions before recomputing. Reset the policy queue with each environment reset. |

## Lab · evaluate on two groups of reset seeds

Run this Bash loop from the [training lab](/notes/lerobot-training/) directory. The tagged evaluator uses `--seed` as a starting reset seed and increments it across episodes. Batch size one makes the rollout order easy to inspect. The shortened 150-step limit is a lab setting. Keep it fixed across models. [Tagged evaluation script](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/scripts/lerobot_eval.py)

```bash
for seed in 101 201; do
  lerobot-eval \
    --policy.path=outputs/pusht-act-smoke/checkpoints/000020/pretrained_model \
    --policy.device=cpu --env.type=pusht \
    --env.observation_height=96 --env.observation_width=96 \
    --env.episode_length=150 --eval.batch_size=1 --eval.n_episodes=5 \
    --seed="$seed" --output_dir="outputs/eval-pusht-$seed"
done
```

**Checkpoint.** Read `eval_info.json` in each output directory. Expect `overall.n_episodes` of 5 per run and saved videos for inspection. Count the true values in `per_task[0].metrics.successes` and report that count out of five alongside `overall.pc_success`, mean summed reward and mean maximum reward. A high maximum reward can indicate near-completion followed by drift. Zero successes would be plausible for a 20-update smoke checkpoint. Inspect videos for early saturation, repeated actions and missed contact. Check preprocessing and command timing before attributing a failure to learning.

Use the same seed blocks when comparing policies. Repeat a block to check run-to-run variability, then use additional unseen resets for a final estimate. For a larger comparison, keep per-episode outcomes and report uncertainty across resets. Track time to success, timeout rate, and any safety violations separately when the task adapter exposes those signals.

## Take the method to the tabletop capstone

In the [tabletop capstone](/notes/capstone-tabletop/), replay commands first to verify ordering and frames, then run the scripted pick-and-place in its simulator, then score imitation on held-out logs. Treat any bridge from Isaac or another simulator as an explicit adapter. Document coordinate frames, the action mode and units, gripper convention, camera transforms, and the control period. Use an adapter smoke test with one known movement and gripper transition before training.

For **offline imitation evaluation**, replay each held-out episode’s recorded observations through the policy with its saved processors. Reset history between episodes. Compare the issued prediction at tick `t` with the recorded action for that tick in original units. Report per-channel mean absolute error (MAE) for continuous actions and gripper agreement for discrete commands. For example, absolute errors of 0.02 rad and 0.04 rad on successive ticks give that joint an episode MAE of 0.03 rad. Average episode scores so long trajectories do not dominate. Compare with a baseline that always issues the training median for each joint and the most frequent training gripper command. The logged observations never respond to the policy’s errors. A **closed-loop rollout** advances the simulator on the policy’s own commands and measures whether it recovers and completes the task.

All motion in this lab is simulated. Real hardware needs its own calibration, controlled workspace, emergency stop, command and rate limits, and supervised validation from conservative initial conditions.

## Self-check

Held-out action error falls, while rollout success falls on the same reset seeds. What could explain it?

<details>
<summary>Check your answer</summary>
<p>Small early errors can steer the controller into observations absent from demonstrations. Offline scoring keeps returning expert observations and can hide the need for recovery. Inspect the first deviation in matched rollouts and check timing and action scaling before changing the model.</p>
</details>
