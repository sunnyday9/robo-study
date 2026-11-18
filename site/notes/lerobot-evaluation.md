---
title: Evaluate an imitation policy
topic: LeRobot
order: "33"
description: Verify the data contract and measure closed-loop behavior across reproducible simulator resets.
prerequisites: An ACT checkpoint and the PushT environment
minutes: 45
---

## Make a failure interpretable

Suppose two policies both time out. One never contacts the T. The other pushes it near the goal, then sends it sideways. Success rates treat both outcomes equally. The videos suggest different next experiments, and neither tells you whether a processor swapped the action coordinates. Your goal is an evaluation another developer can reproduce and debug. Produce a table of outcomes for fixed resets, a matched comparison with one inference setting changed, and a trace or video that explains the first consequential difference.

## Verify the policy–environment contract

Before running a learned policy, verify a known observation and a known action. A shape check can pass when x and y are swapped or an absolute target is interpreted as a delta. In an independent diagnostic rollout, choose a reset where the agent is away from the T and command its current x plus 20 with y held constant. Inspect the numerical position before and after the step and match the direction to the image. Log the requested target and the applied target separately if an adapter clips them. An out-of-range prediction is evidence about the policy or its transforms even when the dispatched command is bounded. This lab uses LeRobot's built-in PushT integration. [Tagged PushT config](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/envs/configs.py) · [PushT observation and action spaces](https://pypi.org/project/gym-pusht/0.1.6/)

| Boundary | Check for this checkpoint |
| --- | --- |
| Simulator → observation | `pixels` becomes `observation.image`, with RGB input at 96 × 96. Confirm channel order and scaling to `[0, 1]` before policy normalization. `agent_pos` becomes `observation.state` in x, y order. |
| Policy → simulator | The saved postprocessor returns an absolute x, y target in simulator units. The simulator’s accepted range is `[0, 512]` per axis. Check bounds, units and direction with a known horizontal target, and count out-of-range predictions. |
| Timing and reset | One command each 0.1 seconds of simulated time. The ACT checkpoint consumes four queued actions before recomputing. Reset the policy queue with each environment reset. |

```text
Reset(seed) clears physics state and the policy queue
   |
   v
o[t] --> image/state mapping --> saved preprocessor --> ACT queue
 ^                                                      |
 |                                                      v
o[t+1] <-- simulator step <-------------------- saved postprocessor
                |
                +--> reward, termination, truncation, success
```

Read the loop from `o[t]` to the command and then to `o[t+1]`. Only the simulator step advances simulated time. Log the replan tick with the issued action if you need to tell a reused target from a new prediction. The tagged evaluator resets the policy and applies both policy and environment processing before stepping. The `observation_height` and `observation_width` settings declare 96 × 96 features in LeRobot's config. In this release those fields are absent from the PushT constructor arguments forwarded by LeRobot, and the pinned gym package itself defaults to 96 × 96 observations. Video render size is a separate setting. Inspect an actual input tensor if you port the lab. [Tagged evaluation rollout](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/scripts/lerobot_eval.py)

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

**Expected checkpoint.** Each output directory should contain `eval_info.json` with `overall.n_episodes` equal to 5 and saved videos. Episode order in this single-task, batch-size-one run corresponds to 101–105 and 201–205. In the Windows CPU smoke run with the numbered 20-update checkpoint, both blocks returned 0/5 successes and five videos each. These short trials verified the evaluation path. They provide little evidence about the performance of a trained policy.

### Read the per-episode evidence

Save the following standard-library script as `read_eval.py`. Run `python read_eval.py outputs/eval-pusht-101/eval_info.json 101` and repeat for the 201 block. The second argument comes from your run command. Keep that command with the JSON because the per-task metric arrays in this release omit the reset seeds.

```python
import json
import sys
from pathlib import Path

result_path, start_seed = Path(sys.argv[1]), int(sys.argv[2])
report = json.loads(result_path.read_text(encoding="utf-8"))
assert len(report["per_task"]) == 1
metrics = report["per_task"][0]["metrics"]
overall = report["overall"]
rows = zip(metrics["successes"], metrics["sum_rewards"],
           metrics["max_rewards"], strict=True)
for seed, (success, total, peak) in enumerate(rows, start_seed):
    print(f"{seed}  success={success}  reward_sum={total:.3f}  reward_max={peak:.3f}")
successes = metrics["successes"]
assert len(successes) == overall["n_episodes"]
print(f'{sum(successes)}/{len(successes)}  ({overall["pc_success"]:.1f}%)')
print("mean sum", overall["avg_sum_reward"], "mean peak", overall["avg_max_reward"])
```

Success is PushT's task flag. The pinned environment succeeds when block coverage exceeds 95%. Its reward is coverage divided by 0.95, capped at 1. A hypothetical four-step reward trace `[0.1, 0.92, 0.4, 0.2]` sums to 1.62 and peaks at 0.92. This trial came closer near the second step than at the end. The two aggregate statistics alone cannot tell you when that peak occurred. A slower trial may sum to more merely by spending longer near the target. Report the actual success count and keep the horizon fixed when interpreting reward sums.

The stock report answers the basic success and reward questions. If you need time to success, timeouts, or invalid commands, log them per trial at the environment boundary. Record the first success tick, `terminated`, `truncated`, and counts of nonfinite or out-of-bounds predictions before clipping. In a lab with a 150-step limit, a full-length trial uses 15 simulated seconds. Report wall-clock inference or render times separately. If a process crashes during a benchmark, preserve the trial and report the infrastructure error explicitly alongside the planned denominator.

### Vary the execution horizon with weights held fixed

Repeat the first block by setting the loop to `for seed in 101; do`, adding `--policy.n_action_steps=1`, and using `--output_dir="outputs/eval-pusht-replan1-$seed"`. Leave the checkpoint, rendering settings, step limit and remaining arguments fixed. The tagged evaluation config loads the checkpoint with policy CLI overrides. The weights and 16-slot prediction stay the same, and the model now queries every tick. [Tagged evaluation config](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/configs/eval.py)

Compare trial 101 with trial 101 and continue through the block. If the two versions act alike until the first contact and separate afterward, examine the next replan and its effect. If both send the agent away from the block at tick 0, examine the input and issued action there first. Walk through the videos and mark the earliest visible failure stage, such as approach, first contact, transport, or alignment into the goal. Then add a narrow trace around that tick with position, commanded target, queue age and reward. If that trace implicates a transform, fix it, rerun the known-movement test, and repeat the same seeds before changing architecture.

The CPU smoke comparison returned 0/5 for both execution horizons on seeds 101–105. On seed 104, peak reward rose from 0.275 to 0.288 while summed reward fell from 8.636 to 7.555 with one action per query. That seed is a place to inspect the rollout. The scores alone cannot establish what happened after contact or which execution horizon would work better with a trained checkpoint.

## Report uncertainty at the trial level

Use matched resets when comparing policies. In an illustrative block, the four-step policy succeeds only on 101 and the one-step policy succeeds on 101 and 104. Report `1/5` and `2/5`, with one win for the one-step version and no reverse flips. The observed difference is 20 percentage points on these seeds. It can be explained by a single trial. A two-sided 95% Wilson interval for even `0/5` is about 0% to 43%, under independent draws from a fixed reset distribution. Treat the prescribed seed blocks as reproducible samples and tie any wider claim to the reset distribution you actually care about.

Repeat a block to check run-to-run variability. Repeating the same seeds does not enlarge coverage of distinct initial conditions, so use additional untouched resets for a final estimate after tuning. If you have enough independently sampled seed pairs, resample whole pairs when estimating uncertainty on a difference. Frames from one rollout are correlated and supply only one success flag. Keep the failure categories with the counts so a similar aggregate can still show a different pattern of behavior.

## Take the method to the tabletop capstone

In the [tabletop capstone](/notes/capstone-tabletop/), replay commands first to verify ordering and frames on one simulation clock. Then run the Isaac Sim 6.1.0 Franka script and score imitation on held-out logs when the feature mapping is implemented. The ROS replay uses Ubuntu 24.04 and Jazzy. LeRobot 0.4.3 PushT runs separately and demonstrates its own observation–action contract. Connecting Franka to a policy requires an explicit adapter for coordinate frames, action mode and units, gripper convention, camera transforms and control period. Test the adapter with one known movement and gripper transition before training.

For **offline imitation evaluation**, replay each held-out episode’s recorded observations through the policy with its saved processors. Reset history between episodes. Compare the issued prediction at tick `t` with the recorded action for that tick in original units. Report per-channel mean absolute error (MAE) for continuous actions and gripper agreement for discrete commands. For example, absolute errors of 0.02 rad and 0.04 rad on successive ticks give that joint an episode MAE of 0.03 rad. Average episode scores so long trajectories do not dominate. Compare with a baseline that always issues the training median for each joint and the most frequent training gripper command. The logged observations never respond to the policy’s errors. A **closed-loop rollout** advances the simulator on the policy’s own commands and measures whether it recovers and completes the task.

All motion in this lab is simulated. Real hardware needs its own calibration, controlled workspace, emergency stop, command and rate limits, and supervised validation from conservative initial conditions.

## Exercises

### Diagnose the first deviation

Held-out action error falls, while rollout success falls on matched seeds. The new policy misses the block near tick 11. What would distinguish a stale queued command from an observation or scaling error?

<details>
<summary>Solution</summary>
<p>Retrieve the observation and raw target for the first different command and note when that command was predicted. Check the saved processor with a known target and repeat the same seed with a one-step execution horizon. If frequent replanning corrects the departure, investigate plan freshness. If both issue the wrong command from a fresh view with the contract verified, inspect coverage at the first off-demonstration state. Logged observations in offline evaluation are unaffected by policy errors.</p>
</details>

### Interpret paired outcomes

Across ten matched resets, policy A succeeds on three and B on four. They share only one success. How many trials flip in each direction, and why should you keep that information?

<details>
<summary>Solution</summary>
<p>B alone succeeds on three seeds and A alone on two. They both succeed once and both fail four times. The observed net gain is one success, but five seeds flip. Examine what distinguishes those five resets, then test the comparison on a larger untouched set.</p>
</details>

## Common misconceptions

- **Peak reward is the success rate.** Peak reward describes the best task progress within a rollout. Use the simulator's success flag for the trial count.
- **Low offline error guarantees recovery.** Start from the same reset and run the policy's own actions. It may encounter observations that expert logs never contained.
- **A simulator run meets the physical control deadline.** Simulated time can advance one tick even if inference takes longer than that tick in wall time.

## Summary

Check sensor and action semantics with a known movement. Report numerators and denominators on matched resets, then examine the first failure stage before changing the model. Keep the seed list and execution schedule with each result so another developer can reproduce the comparison.
