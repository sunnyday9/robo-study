---
title: Train an imitation policy
topic: LeRobot
order: "32"
description: Compare ACT and Diffusion Policy, train an ACT checkpoint, and inspect its processors.
prerequisites: Episode splits, PyTorch basics, and the recording lab setup
minutes: 55
---

## Decide what the model predicts

Behavior cloning fits a mapping from observations to demonstrated actions. A chunked policy predicts several commands together, which can preserve a coherent maneuver through contact. **Prediction horizon** is how far ahead the model predicts. **Execution horizon** is how many of those commands the controller consumes before querying the policy again. At 10 Hz, executing four actions gives the environment 0.4 seconds to evolve before the next prediction. Shortening that interval gives more opportunities to respond to disturbances and costs more inference.

| Policy | How it models actions | What to watch |
| --- | --- | --- |
| ACT | A Transformer predicts a chunk in one forward pass. With the variational encoder enabled, it learns a latent representation of demonstration behavior. The default inference path uses a zero latent. | Inspect sequences for hesitation if demonstrations chose different approaches in similar observations. |
| Diffusion Policy | Conditions iterative denoising on recent observations to sample an action sequence. Different samples can represent different plausible maneuvers. | Measure sampling latency against the control period. A coherent sample can still arrive too late. |

Start with ACT to check the pipeline. Compare architectures on the same data, reset seeds and task metrics. Their training losses describe different objectives and have different scales. [ACT paper](https://arxiv.org/abs/2304.13705) · [Diffusion Policy paper and project](https://diffusion-policy.cs.columbia.edu/) · [Tagged ACT config](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/policies/act/configuration_act.py) · [Tagged Diffusion config](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/policies/diffusion/configuration_diffusion.py)

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

**Checkpoint.** Look for a finite loss and `outputs/pusht-act-smoke/checkpoints/000020/pretrained_model/`. Twenty updates exercise the data-to-checkpoint path. Judging learning requires a longer run and evaluation. If decoding fails before the first batch, open a video sample with the selected backend and check that it supports the dataset’s AV1 stream. If the loss is nonfinite, inspect a decoded batch and its per-feature statistics before changing optimization settings.

## Keep preprocessing with the weights

ACT uses mean and standard deviation for its features by default. Diffusion Policy uses min–max scaling for state and action by default. The training CLI defaults to ImageNet mean and standard deviation for camera features. A policy predicts in the target’s training representation, so the saved postprocessor must undo action normalization before the command reaches the simulator.

Keep the entire `pretrained_model/` directory together. It contains the weights, policy and training configs, and preprocessor and postprocessor definitions with their saved state. Keep the sibling `training_state/` if you need to resume training. Record the dataset revision, split IDs, seed and feature contract with the result. [Tagged checkpoint writer](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/utils/train_utils.py)

## Self-check

You load the model weights alone and send its predictions straight to PushT. The targets cluster near zero even though demonstrations covered the workspace. What do you check?

<details>
<summary>Check your answer</summary>
<p>Inspect the saved action postprocessor. ACT predicts standardized targets. Undo its training normalization once, then check the resulting absolute positions against PushT’s action bounds. Use the matching preprocessor for observations.</p>
</details>

Take the complete checkpoint to [closed-loop evaluation](/notes/lerobot-evaluation/).
