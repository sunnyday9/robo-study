---
title: Collect and check demonstrations
topic: LeRobot
order: "092"
description: Write a small simulated dataset and verify what each saved frame means.
prerequisites: Episode structure and basic Python
minutes: 45
---

## Make the recorder prove its ordering

It is easy to produce a dataset that looks healthy on disk and teaches the wrong behavior. A recorder can attach a command to the frame that shows its effect. A file-count check will pass because every tick still contributes one image, one state and one action. Build a diagnostic input into the collector before asking a person to record hours of demonstrations. In this lab, your target is two episodes you can reopen, plus a trace showing where a known target change enters the file and where the measured position first responds.

## Choose what generates the action

In teleoperation, a person drives a leader arm or another input device and a follower executes commands. A good operator can demonstrate contact and recovery maneuvers that would be expensive to program. The inputs still pass through calibration, coordinate conversion, limits and potentially an interface-specific processor. Log what reached the controller. If a user requests a gripper value of 1.1 and your command processor clamps it to 1.0, the desired target for standard behavior cloning is 1.0. Save the raw request separately if you want to understand how often the operator hits a limit.

A scripted rollout computes the command in code. Use a script when you need repeatable movements or want to isolate the effect of one change. A flawless straight-line script can still produce brittle training data if its coverage excludes off-center object poses; a human can supply recoveries, but operators can also demonstrate incompatible strategies from nearly identical observations. A random command stream is helpful for plumbing checks because it exercises a range of action values. The [training lab](/notes/lerobot-training/) uses the public PushT demonstrations for task supervision. [LeRobot recording entry point at v0.4.3](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/scripts/lerobot_record.py)

| Collection step | What to preserve |
| --- | --- |
| Reset | Episode ID, task and provenance such as simulator seed or operator session. |
| Observe and act | The pre-action camera and state, and the command actually sent after any clipping. |
| End episode | Outcome and reason for ending. A time limit and task success answer different questions. |

### Put the save boundary at the decision

In the pinned simulator, each environment step drives the agent toward an absolute two-coordinate target. The control loop advances 0.1 s of simulated time. Inside it, the simulator applies a position/velocity feedback controller over 0.01 s physics substeps. These rates describe simulated work. If writing a frame takes 250 ms on the host, the next PushT step still advances 0.1 s of simulated time. On a live robot, a blocking write can cause deadline misses while the physical system continues moving. A buffered writer can avoid blocking, but then its queue needs a capacity and an explicit policy for preserving or dropping samples. [Pinned gym-pusht package](https://pypi.org/project/gym-pusht/0.1.6/)

```text
reset(seed) --> obs[0]
                  |
tick 0     target[0] = command(obs[0])
           add_frame(obs[0], target[0])
           step(target[0]) --------------> obs[1], outcome[0]
                                              |
tick 1     target[1] = command(obs[1]) <-------+
           add_frame(obs[1], target[1])
           step(target[1]) --------------> obs[2], outcome[1]
                                              |
           if done: save_episode() <----------+
```

The second observation belongs to the second decision, even though the first command produced it. The terminal outcome belongs to the transition that just ran. If an exception occurs after buffering a frame but before the action has executed, treat that episode as incomplete. Commit a whole episode after its loop finishes. Finalizing closes writers so completed shards can be read back. A loadable file is a structural checkpoint and reopening it gives you a chance to compare persisted values with the trace from the live loop.

## Lab · record two simulated episodes

Use a Linux Bash shell with Python 3.12 in a fresh work directory. The commands install CPU wheels. The recorder stores images directly in Parquet. The later training lab reads video from the public PushT dataset and uses the PyAV decoder. If installation fails building `evdev` with a missing `Python.h`, use a Python distribution with development headers or install your distribution’s matching headers and C compiler. [Tagged install guide](https://github.com/huggingface/lerobot/blob/v0.4.3/docs/source/installation.mdx) · [PyTorch CPU wheels](https://pytorch.org/get-started/previous-versions/#v271) · [PushT package](https://pypi.org/project/gym-pusht/0.1.6/)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install torch==2.7.1 torchvision==0.22.1 \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install 'lerobot[pusht]==0.4.3' 'gym-pusht==0.1.6'
python -c 'from importlib.metadata import version; print(version("lerobot"))'
```

Save the Python as `collect_pusht.py` and run `python collect_pusht.py` from the same shell. The defaults retain the original two random rollouts. A second mode holds the initial x, y target and then makes one horizontal target change at a chosen tick. The schema and environment are the same in both modes. Choose a fresh output directory for every run. The seeds and cutoff are part of the run record. This example runs locally without a physical robot or Hub upload.

```python
from argparse import ArgumentParser

import gymnasium as gym
import gym_pusht  # Registers PushT.
from lerobot.datasets.lerobot_dataset import LeRobotDataset

parser = ArgumentParser()
parser.add_argument("--output", default="pusht-qa")
parser.add_argument("--jump-tick", type=int, choices=range(1, 19))
args = parser.parse_args()

env = gym.make("gym_pusht/PushT-v0", obs_type="pixels_agent_pos",
               render_mode="rgb_array", max_episode_steps=20)
dataset = LeRobotDataset.create(
    "local/pusht-qa", root=args.output, fps=10, use_videos=False,
    features={
        "observation.image": {"dtype": "image", "shape": (96, 96, 3),
                              "names": ["height", "width", "channel"]},
        "observation.state": {"dtype": "float32", "shape": (2,),
                              "names": ["x", "y"]},
        "action": {"dtype": "float32", "shape": (2,), "names": ["x", "y"]},
    },
)
try:
    for seed in (11, 12):
        obs, _ = env.reset(seed=seed)
        env.action_space.seed(seed)
        start = obs["agent_pos"].astype("float32").copy()
        target = start.copy()
        target[0] += 20 if start[0] <= 256 else -20
        tick = 0
        terminated = truncated = False
        while not (terminated or truncated):
            if args.jump_tick is None:
                action = env.action_space.sample()
            else:
                action = (start if tick < args.jump_tick else target).copy()
            assert env.action_space.contains(action)
            dataset.add_frame({
                "observation.image": obs["pixels"],
                "observation.state": obs["agent_pos"].astype("float32"),
                "action": action,
                "task": "Push the T into the goal",
            })
            obs, _, terminated, truncated, info = env.step(action)
            tick += 1
        dataset.save_episode()
        print(seed, tick, info["is_success"], terminated, truncated)
finally:
    dataset.finalize()
    env.close()

saved = LeRobotDataset("local/pusht-qa", root=args.output)
assert saved.num_episodes == 2
print(saved.num_frames, saved[0]["observation.image"].shape)
if args.jump_tick is not None:
    for tick in range(args.jump_tick - 1, args.jump_tick + 2):
        row = saved[tick]
        if row["episode_index"].item() != 0:
            break
        print(tick, f'{row["timestamp"].item():.1f}',
              row["observation.state"].tolist(), "->", row["action"].tolist())
```

The original random run wrote and reopened **two episodes and 40 total frames** in the course's recorder check. Each episode is capped at 20 steps. Expect a decoded image of shape `(3, 96, 96)`. Run `python audit_pusht.py pusht-qa/data/chunk-000/file-000.parquet --holdout 1` with the [shard audit](/notes/lerobot-data/) to verify continuity. The one-episode holdout exercises the audit on this fixture. It is too small and its behavior too artificial to estimate generalization. The printed fields are seed, saved steps, success, termination and truncation. In a collection for training, write these to a manifest keyed by episode ID and preserve any abort or retry reason. If the file cannot be reopened, check that the episode was saved and `finalize()` ran before inspecting the renderer. [Tagged dataset writer](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/datasets/lerobot_dataset.py)

### Move one target change by one tick

```bash
python collect_pusht.py --jump-tick 5 --output pusht-jump-5
python collect_pusht.py --jump-tick 6 --output pusht-jump-6
```

The seed and target displacement are fixed across these runs. The printed action should change at 0.5 s in the first run and 0.6 s in the second. In a Windows CPU check with the pinned packages, seed 11's x-target changed from 103 to 123 at tick 5, while measured x still read 103. At tick 6, measured x read 108.91. In the second run both events moved one tick later. The exact response for another seed depends on dynamics and contact. First look for the target change on the expected row, then find where the state starts to respond. If the position has already responded *on* the change row, compare the state passed to `add_frame` with the state returned by `step`. If only the image appears shifted, inspect camera ordering, overlays and buffering separately from the state signal. Rerun the same seed and jump tick after the fix so the diagnostic remains comparable.

On hardware, adapt the probe through the hardware-specific calibration and motion limits. Verify ordering and bounds, preserve original capture stamps, and check for frozen frames, delayed commands and saturation in a small pilot. One simulation time authority is enough for the [tabletop replay contract](/notes/capstone-tabletop/). When streams come from different devices, establish how their clocks are aligned and report missing or stale frames before exporting to fixed-rate data. A single nominal FPS field cannot report that skew.

## Exercises

### Diagnose the image and state separately

At tick 5 the target changes, the image shows the agent already in motion, and the saved numerical position first changes at tick 6. Which trace would you collect next?

<details>
<summary>Solution</summary>
<p>Log the image capture stamp and a frame identifier before and after the call that advances physics. Compare them with the saved state and the command stamp. Check whether the apparent motion is a target overlay or actual movement. If the saved image came from after the step, fix the image association and repeat the same target-change probe.</p>
</details>

### Plan demonstrations for a recovery

A scripted expert succeeds whenever it contacts the block centrally. The learned policy often first touches a corner and then keeps pushing in the wrong direction. What should your next recording pass include?

<details>
<summary>Solution</summary>
<p>Start some demonstrations from off-center placements and include successful recovery after an initial corner touch. Record the reset conditions and describe the recovery phase. Keep original easy cases as a baseline, then hold out separate resets with off-center contacts to test whether the additional data helped.</p>
</details>

## Common misconceptions

- **A longer recording is always more informative.** Targeted coverage of the hard approaches and recoveries can add behavior that many repeated easy resets never show.
- **A successful save proves causal ordering.** The writer validates feature structure. The controlled target change lets you test the association with observed motion.
- **FPS measures how fast the recorder ran.** It defines the dataset's tick spacing here. Wall time and missed deadlines need their own measurements.

## Summary

Record the state available at decision time, the command sent, and the resulting end condition. Save and reopen short episodes, then challenge the recorder with a known input change. Once you can find that change in the stored file, use trajectories with adequate task and recovery coverage to [train a policy](/notes/lerobot-training/).
