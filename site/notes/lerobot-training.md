---
title: Train an imitation policy
topic: LeRobot
order: "093"
description: Compare ACT and Diffusion Policy, train an ACT checkpoint, and inspect its processors.
prerequisites: Episode splits, PyTorch basics, and the recording lab setup
minutes: 55
---

## Prove the route from a batch to a command

<figure class="lesson-figure">
  <a href="/assets/figures/policy-workflow.svg"><img src="/assets/figures/policy-workflow.svg" width="640" height="494" loading="lazy" decoding="async" alt="Record observation-action pairs, train with processing, save the model and processors together, and evaluate decoded commands in closed loop."></a>
  <figcaption>Follow one sample across the workflow. Saving only the weights leaves out the conversions that give a prediction its meaning at rollout time.</figcaption>
</figure>

If a trained pusher drives to the origin, your first question is whether it *chose* the origin. A policy can predict a reasonable action in standardized coordinates while the controller reads those two numbers as absolute position. A model can also choose a coherent maneuver and keep executing it after the object has moved away. Build a checkpoint that can tell these failures apart. The observable target is a finite training update, a reloadable policy with its processors, and a trace that says which observation generated each issued command.

## Decide what the model predicts

Behavior cloning uses the demonstrated action as a supervised target. The simulator's reward is useful for measuring behavior later. ACT and Diffusion Policy in this lecture learn from the action sequences in the dataset. In a one-step policy, you infer after every observation. In a chunked policy, several targets are generated together, which can preserve a coherent maneuver through contact. **Prediction horizon** is the span the model represents. **Execution horizon** is how many targets you actually consume before querying the policy again. A longer execution horizon saves forward passes but leaves more ticks controlled by a plan conditioned on an older observation.

| Policy | How it models actions | What to watch |
| --- | --- | --- |
| ACT | A Transformer predicts a chunk in one forward pass. The training-time variational encoder can use the recorded action chunk. At ordinary inference the model uses a zero latent. | Inspect for hesitation near contact when similar demonstrations chose different approaches. |
| Diffusion Policy | An observation-conditioned denoising network iteratively samples an action sequence. Samples can represent distinct plausible maneuvers. | Measure the sampling latency and whether consecutive replans agree when a maneuver is partway through. |

Start with ACT to check the pipeline. Compare architectures on the same data, reset seeds and task metrics. Their training losses describe different objectives and have different scales. [ACT paper](https://arxiv.org/abs/2304.13705) · [Diffusion Policy paper and project](https://diffusion-policy.cs.columbia.edu/) · [Tagged ACT config](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/policies/act/configuration_act.py) · [Tagged Diffusion config](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/policies/diffusion/configuration_diffusion.py)

### Follow the target into the loss

For this ACT lab, a batch of two samples contains current images of shape `(2, 3, 96, 96)` and chunks with shape `(2, 16, 2)`. Each chunk predicts x and y at offsets 0 through 15. Training compares each predicted target with the demonstrated target at the same offset. At an episode boundary, the loader repeats an edge target and sets a padding flag, as shown in the [dataset lab](/notes/lerobot-data/). In this release ACT multiplies the absolute error by the inverse padding mask and then takes the tensor mean. For one coordinate and four slots, errors `[0.2, 0.4, 0.6, 5.0]` with the last two masked yield `(0.2 + 0.4) / 4 = 0.15`. The 5.0 contributes no reconstruction gradient. The two zeroed entries still count toward the denominator. With the variational encoder enabled, ACT adds a weighted KL term that regularizes the learned latent distribution toward a standard normal. Log reconstruction and KL separately when diagnosing a stalled run. [Tagged ACT loss and forward pass](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/policies/act/modeling_act.py)

Diffusion Policy builds a noise-corrupted version of the whole action trajectory at a sampled diffusion timestep. With the tagged default `epsilon` target, it uses squared error on the predicted noise. At inference it starts with noise and runs the reverse process conditioned on recent observations. The tagged default uses two observation ticks. A 16-slot prediction spans `t − 1` through `t + 14` and execution begins at the slot for `t`. When inspecting Diffusion Policy losses near a trajectory edge, check its padding-mask setting independently of ACT's behavior. [Tagged Diffusion training and sampling code](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/policies/diffusion/modeling_diffusion.py)

Consider a demonstration set where two valid approaches to the same block start with x-targets of 180 and 320. If the current input leaves the intended approach ambiguous, a point prediction can land between them. Plotting each generated trajectory over the scene can show whether it commits to a valid route. Diffusion can represent multiple routes, at the cost of more computation and the possibility of switching routes across replans. Another experiment is to give the model a disambiguating task signal or align the demonstrations around one consistent approach. The change you choose should follow from what you see at the first ambiguous decision.

### Trace a replan

```text
Tick                        8      9     10     11     12
Observation available       o8     o9    o10    o11    o12
Model runs?                 yes     ·      ·      ·    yes
Issued x target             210    225    243    260    228
Plan was made at tick       8      8      8      8      12
                                ^ block deflects here
```

This is an illustrative trace for the lab's 16-step predictions with four steps executed. At tick 10 the simulator has a fresh observation, yet the policy takes its next target from tick 8's queue. At tick 12 it replans using the new view. Each group executes 0.4 s of simulated behavior. With one action per query, the policy could respond at tick 9 or 10, depending on when the disturbance becomes observable. Watch for shifts in both recovery and command continuity. More frequent replans can change the sequence at every tick and, on a time-constrained controller, increase the chance of delayed commands.

## Lab · train a small ACT checkpoint

Run this Bash command in the [LeRobot v0.4.3 environment](/notes/lerobot-recording/), using a fresh output path. The first run downloads the public dataset, including its video shard. The audited split in the data chapter demonstrated episode partitioning. This smoke run uses all the public demonstrations, and the next chapter evaluates on fresh simulator resets. For a held-out offline experiment, materialize a training-only dataset with its own statistics. In this release, `dataset.episodes` selects the loaded rows while training still reads normalization statistics from dataset metadata. [Tagged dataset factory](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/datasets/factory.py) · [Tagged training script](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/scripts/lerobot_train.py)

```bash
lerobot-train \
  --dataset.repo_id=lerobot/pusht \
  --dataset.revision=b1c3ecbae7f244acc039a3dbc255a00dad1372b9 \
  --dataset.root=./data/pusht-v3-pinned \
  --dataset.video_backend=pyav \
  --policy.type=act --policy.device=cpu --policy.push_to_hub=false \
  --policy.pretrained_backbone_weights=null \
  --policy.chunk_size=16 --policy.n_action_steps=4 \
  --steps=20 --batch_size=2 --num_workers=0 --seed=17 \
  --log_freq=5 --eval_freq=0 --save_freq=20 \
  --output_dir=outputs/pusht-act-smoke
```

**Expected checkpoint.** Look for a finite logged loss and `outputs/pusht-act-smoke/checkpoints/000020/pretrained_model/`. This is a pipeline smoke test. Twenty updates give you a concrete artifact to inspect and little evidence about the quality of the learned maneuver. A Windows CPU check completed the 20 updates and wrote the numbered checkpoint. The training CLI then hit a Windows permission error creating the `last` symlink. Use the numbered path for the processor check and evaluation. The lab's Linux setup was not run end to end in that check.

Use the first failed stage to choose your next probe. If the loader shows AV1 errors before the first update, use the [decoded-window inspection](/notes/lerobot-data/) to request one image through PyAV. Check the download and decoder before changing the model. If loss becomes nonfinite after a batch arrives, record the min and max for state, action and image immediately before and after the preprocessor and check the padding mask. Once the pipeline works, a useful training-side probe is to repeatedly optimize the same preprocessed batch and watch its reconstruction error. A failure to fit that batch suggests an optimization or representation bug. Success on a repeated batch tells you little about fresh observations. For a real offline comparison, use the training-only split and report held-out results in original units.

## Keep preprocessing with the weights

Follow the representations from disk to the simulator. The loader decodes RGB images to channel-first floats in `[0, 1]`. At training time ACT's policy preprocessor handles input naming, batching, device placement and feature normalization, including action targets. The training CLI uses ImageNet mean and standard deviation for camera features by default. State and action each have their own fitted mean and standard deviation. Diffusion Policy defaults to min–max scaling for state and action, so the same numeric tensor can correspond to different physical commands. At evaluation the environment code constructs the input layout, the saved policy preprocessor applies the training transform, and the saved postprocessor inverts the output transform before simulator dispatch. [Tagged ACT processors](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/policies/act/processor_act.py)

For an illustrative x-target mean of 250 and standard deviation of 50, a model prediction of 0.6 should reach the environment as `250 + 50 × 0.6 = 280`. Sending 0.6 directly aims toward the workspace edge. Applying the inverse twice would produce 14,250. Keep the entire `pretrained_model/` directory together so the config and processor state travel with the weights. For resumable training retain the sibling `training_state/` as well. Record the source data revision, original split IDs, seed and feature contract. [Tagged checkpoint writer](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/utils/train_utils.py)

### Check one processor with a known target

After training, run this CPU check from the same work directory. The zero vector is a known ACT model-space value. The result should match the raw action mean in the pinned dataset's metadata, within floating point error. The check exercises the packaged postprocessor independently of the trained weights.

```python
import json
from pathlib import Path

import torch
from lerobot.configs.policies import PreTrainedConfig
from lerobot.policies.factory import make_pre_post_processors

checkpoint = Path("outputs/pusht-act-smoke/checkpoints/000020/pretrained_model")
config = PreTrainedConfig.from_pretrained(checkpoint)
_, postprocess = make_pre_post_processors(config, pretrained_path=str(checkpoint))
stats_file = Path("data/pusht-v3-pinned/meta/stats.json")
action_mean = torch.tensor(json.loads(stats_file.read_text())["action"]["mean"])
raw_target = postprocess(torch.zeros((1, 2)))[0]
print(raw_target.tolist(), action_mean.tolist())
torch.testing.assert_close(raw_target, action_mean)
```

In the CPU check, both printed vectors were approximately `[228.24, 293.99]`. For a controlled fault, replace only `raw_target = postprocess(torch.zeros((1, 2)))[0]` with `raw_target = torch.zeros(2)`. This reproduced an assertion failure because it compared a normalized prediction against an absolute coordinate. If the original check fails too, trace which processor files the loader used and compare the stored training action statistics before retraining. Restore the inverse, then take the complete checkpoint to [closed-loop evaluation](/notes/lerobot-evaluation/) to vary queue length while holding weights fixed.

## Exercises

### Diagnose a stale plan

At tick 32 an ACT policy recomputes, and at tick 33 the block slips. With four actions per query, when can a new observation first affect a prediction? What experiment isolates the queue's contribution?

<details>
<summary>Solution</summary>
<p>After consuming ticks 32–35, it first replans at tick 36. Retain the weights and 16-step output, change execution to one action per query, and compare the first post-slip command, subsequent contact, and inference cost on the same reset. If both cadences issue equally bad fresh plans, investigate recovery coverage or the observation contract.</p>
</details>

### Trace the two losses

A teammate compares an ACT loss of 0.25 to a diffusion loss of 0.12 on the same dataset. Which evidence would let you choose a model for deployment in a simulator?

<details>
<summary>Solution</summary>
<p>ACT combines masked absolute action error with latent regularization. Diffusion's default predicts injected noise with squared error. Compare the actual commands in simulator units on held-out logs, then task outcomes and inference time on matched resets and a fixed control schedule. Inspect failure trajectories even if the mean scores agree.</p>
</details>

## Common misconceptions

- **ACT sends the full predicted chunk.** Under the lab config, the model predicts 16 actions and queues the first four. Queue length is an inference choice.
- **Every denoising step advances the robot.** The denoising schedule is internal to the model. The control clock advances when an issued target reaches the environment.
- **Weights contain every preprocessing choice.** The normalization state is saved with the processor definitions. Reload the complete checkpoint and test a known action.

## Summary

Trace the exact training target, its normalization, the model's loss, and the queue that produces real commands. A tiny run makes each interface inspectable. Test the processor with a known value and change one inference setting at a time to learn which failures come from a controller's schedule.
