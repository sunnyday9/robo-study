---
title: Collect and check demonstrations
topic: LeRobot
order: "31"
description: Write a small simulated dataset and verify what each saved frame means.
prerequisites: Episode structure and basic Python
minutes: 45
---

## Choose what generates the action

In teleoperation, a person moves a leader arm or controller and a follower robot executes the command. The logged target comes from the teleoperator. In a scripted simulation rollout, code computes a command and the simulator advances its physics. Both can supply observation–action examples. To learn a task, you need demonstrations that actually cover its steps, including approaches and recoveries. A random rollout is a quick way to check a recorder and a poor source of supervision for completing a task. [LeRobot recording entry point at v0.4.3](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/scripts/lerobot_record.py)

| Collection step | What to preserve |
| --- | --- |
| Reset | Episode ID, task and provenance such as simulator seed or operator session. |
| Observe and act | The pre-action camera and state, and the command actually sent after any clipping. |
| End episode | Outcome and reason for ending. A time limit and task success answer different questions. |

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

Save the runnable Python as `collect_pusht.py` and run `python collect_pusht.py` from the same shell. Use a fresh `pusht-qa` output directory each time. The seeds and the 20-step cutoff are part of the run record. This example uses no physical robot or Hub upload.

```python
import gymnasium as gym
import gym_pusht  # Registers PushT.
from lerobot.datasets.lerobot_dataset import LeRobotDataset

env = gym.make("gym_pusht/PushT-v0", obs_type="pixels_agent_pos",
               render_mode="rgb_array", max_episode_steps=20)
dataset = LeRobotDataset.create(
    "local/pusht-qa", root="pusht-qa", fps=10, use_videos=False,
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
        terminated = truncated = False
        while not (terminated or truncated):
            action = env.action_space.sample()
            dataset.add_frame({
                "observation.image": obs["pixels"],
                "observation.state": obs["agent_pos"].astype("float32"),
                "action": action,
                "task": "Push the T into the goal",
            })
            obs, _, terminated, truncated, info = env.step(action)
        dataset.save_episode()
        print(seed, info["is_success"], terminated, truncated)
finally:
    dataset.finalize()
    env.close()

saved = LeRobotDataset("local/pusht-qa", root="pusht-qa")
assert saved.num_episodes == 2
print(saved.num_frames, saved[0]["observation.image"].shape)
```

**Checkpoint.** Expect two episodes of at most 20 frames each and a decoded image of shape `(3, 96, 96)`. Point the [shard audit](/notes/lerobot-data/) at `pusht-qa/data/chunk-000/file-000.parquet` and run the structure and timing assertions. Skip the 20-episode holdout step for this two-episode fixture. The printed success and cutoff flags are QA output. For a training collection, keep an outcome manifest keyed by episode ID alongside the saved data. An unreadable Parquet footer is a reason to check whether `finalize()` ran. [Tagged dataset writer](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/datasets/lerobot_dataset.py)

Before collecting on hardware, verify calibration, joint ordering and bounds with the hardware-specific procedure. Audit a short pilot for frozen images, action saturation, and observation–action lag before increasing volume. Compare a visible motion onset with the corresponding commanded motion and keep the capture timestamps when measuring sensor latency.

## Self-check

The images move one tick *before* the command changes in every saved episode. What should you inspect first?

<details>
<summary>Check your answer</summary>
<p>Check whether the recording loop paired the command with the observation returned after stepping, or joined asynchronous camera and command streams with a one-frame offset. Inspect capture and command timestamps around a known change.</p>
</details>

Carry the same observation-before-action convention into the [tabletop capstone](/notes/capstone-tabletop/). Use the expert PushT demonstrations in the [training lab](/notes/lerobot-training/).
