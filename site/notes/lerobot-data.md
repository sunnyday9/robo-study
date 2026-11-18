---
title: Read a robot learning dataset
topic: LeRobot
order: "30"
description: Inspect recorded observations and commands, audit their timing, and split by episode.
prerequisites: Python and basic supervised learning
minutes: 35
---

## Decide what one row teaches

A pushing policy can learn to move a tick too late while achieving excellent held-out loss. Adjacent camera frames look alike, and the pusher often pursues the same target for several ticks. Shift the labels or split neighboring rows across training and test, and every tensor may still have the right shape. Your first deliverable is an audit you can run before fitting anything. Pick an episode, trace an observation to its outgoing command and next state, then show that the episode and its training windows stay on one side of the split.

LeRobot stores and loads demonstrations and uses them for learning. In the independent PushT simulator, a circular agent moves a T-shaped block toward a goal. Start with the public traces so you need neither a simulator process nor hardware. This track uses LeRobot **v0.4.3** and pins a PushT revision whose storage format is **v3.0**. The revision identifies the exact data, while the format version tells the reader how to open it. [LeRobot release](https://github.com/huggingface/lerobot/releases/tag/v0.4.3) · [PushT dataset metadata](https://huggingface.co/datasets/lerobot/pusht/blob/b1c3ecbae7f244acc039a3dbc255a00dad1372b9/meta/info.json)

## Read an episode as a trajectory

An episode begins at a reset and ends at an outcome or collection cutoff. The row at tick `t` pairs the observation available before the decision with the command issued at that tick. The command produces a transition to the next observation. Fields such as `next.reward` describe that transition. They can help you audit a trajectory, but supplying the resulting image or reward as input at `t` gives the policy information from its own future.

![Two PushT episodes shown side by side. Each row pairs a pre-command observation with the command at that tick. The timestamp resets in the second episode, which stays entirely in the held-out split.](/assets/lerobot-episode-timeline.svg)

Read across each tick in the diagram to find the command associated with an observation. Follow the episode forward to find the observation affected by that command. Both resets start their row clocks at zero, so `episode_index` is part of the address whenever you use `frame_index` or `timestamp`.

| Field | How to interpret it in PushT |
| --- | --- |
| `observation.image` | RGB view. The dataset stores frames in video and declares their shape as height × width × channels. |
| `observation.state` | Measured agent position, two coordinates. |
| `action` | Commanded target position, two coordinates in the simulator’s 512-unit workspace. Equal shape does not imply equal meaning. |
| `episode_index`, `frame_index`, `timestamp` | Episode ID, episode-local step and episode-relative time in seconds. At 10 Hz, one frame tick is 0.1 s. |
| `index`, `task_index` | Global row index and a key into task metadata. |

The first actual row stores measured position `[222, 97]` and absolute target `[233, 71]`. Their difference is `[11, -26]` workspace units. Sending that difference as an action would ask the simulator to aim at `(11, -26)`. The next row's recorded position is about `[225.25, 89.31]`, partway toward the target. Exact equality would require instantaneous motion on that tick. To diagnose a delay, inspect when movement begins around a decisive change in target.

Version 3 packs many episodes into shared Parquet and video shards. Episode metadata gives the row range and the video offset for each camera. If an episode starts 12.4 s into the MP4, its row at episode time 0.3 s requests video time 12.7 s. Seeking to 0.3 s in that MP4 could silently select a different scene. Use the dataset loader for this join. The storage schema describes a 96 × 96 × 3 image, while the loader supplies a channel-first tensor. [Tagged dataset implementation](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/datasets/lerobot_dataset.py) · [PushT action and observation spaces](https://github.com/huggingface/gym-pusht#description)

For a recorder or exporter, preserve acquisition stamps separately from the regular row timestamp whenever a sensor runs asynchronously. In an illustrative join, tick 7 sends a command at simulation time 0.700 s. Available images have acquisition times of 0.671 s and 0.715 s. With a 40 ms age budget, choose 0.671 s if that image was already available to the controller. It is 29 ms old, and the closer image is from the future. If the budget is 20 ms, mark the sample missing or follow an explicit discard rule. A previous-frame join preserves causality but gives older observations when frames drop. Waiting for a new image gives fresher inputs and changes when you act. Keep timing in one simulation clock and measure each delay at its own boundary. [Tabletop capture contract](/notes/capstone-tabletop/)

## Lab · audit a shard offline

Install PyArrow with `python -m pip install pyarrow` in a virtual environment. Download [the pinned PushT Parquet shard](https://huggingface.co/datasets/lerobot/pusht/resolve/b1c3ecbae7f244acc039a3dbc255a00dad1372b9/data/chunk-000/file-000.parquet) as `file-000.parquet`. The runnable Python below reads only that local file. It needs neither PyTorch nor video decoding.

```python
from argparse import ArgumentParser
from collections import defaultdict
from math import isclose, isfinite

import pyarrow.parquet as pq

parser = ArgumentParser()
parser.add_argument("shard", nargs="?", default="file-000.parquet")
parser.add_argument("--holdout", type=int, default=20)
args = parser.parse_args()
columns = ["episode_index", "frame_index", "timestamp",
           "observation.state", "action"]
episodes = defaultdict(list)
for row in pq.read_table(args.shard, columns=columns).to_pylist():
    episodes[row["episode_index"]].append(row)

for episode, rows in episodes.items():
    for tick, row in enumerate(rows):
        location = (episode, tick)
        assert row["frame_index"] == tick, location
        assert isclose(row["timestamp"], tick / 10, abs_tol=1e-4), location
        for key in ("observation.state", "action"):
            assert len(row[key]) == 2 and all(map(isfinite, row[key])), (location, key)

ids = sorted(episodes)
assert 0 < args.holdout < len(ids)
train_ids, held_out_ids = ids[:-args.holdout], ids[-args.holdout:]
assert set(train_ids).isdisjoint(held_out_ids)
print(f"{len(ids)} episodes, {sum(map(len, episodes.values()))} rows")
print(f"train {len(train_ids)}, held out {len(held_out_ids)}")
for row in episodes[ids[0]][:5]:
    print(row["frame_index"], f'{row["timestamp"]:.1f}',
          row["observation.state"], "->", row["action"])
```

Save as `audit_pusht.py` and run `python audit_pusht.py`. The course's measured audit of the pinned file found **206 episodes and 25,650 rows**. The first row should print `0 0.0 [222.0, 97.0] -> [233.0, 71.0]`. The code assumes this file contains complete trajectories starting at frame zero. For a general multi-shard dataset, locate the complete episode before applying continuity checks. If an assertion fires, inspect the reported episode and its neighbors in original order. Sorting by a broken timestamp can erase evidence of a recorder or reader bug.

Vary one input to the checker. Change `tick / 10` to `tick / 9` in a copy of the script. The expected first failure in episode 0 is tick 1. Its stored time is about 0.100 s, while the modified assumption gives 0.111 s, outside the 0.0001 s tolerance. Restore 10 Hz after explaining the failure. Compare the first five state–target pairs and ask whether the state is tracking a target or simply duplicating it. An apparently regular row cadence can still hide a frozen camera or a command applied a tick late.

### Inspect a decoded action window

With the environment from [recording](/notes/lerobot-recording/) and the public data path from [training](/notes/lerobot-training/), inspect two windows within episode 0. This optional step reads video and shows how stored rows become training examples. Save as `inspect_pusht.py` and run it from the training lab directory.

```python
from lerobot.datasets.lerobot_dataset import LeRobotDataset

dataset = LeRobotDataset(
    "lerobot/pusht",
    root="./data/pusht-v3-pinned",
    revision="b1c3ecbae7f244acc039a3dbc255a00dad1372b9",
    episodes=[0],
    delta_timestamps={"action": [0.0, 0.1, 0.2, 0.3]},
    video_backend="pyav",
)
for index in (0, len(dataset) - 1):
    row = dataset[index]
    image = row["observation.image"]
    print(row["frame_index"].item(), tuple(image.shape),
          float(image.min()), float(image.max()))
    print(row["action"].tolist(), row["action_is_pad"].tolist())
```

The expected image shape is `(3, 96, 96)` with decoded values in `[0, 1]`. A mismatch calls for checking the decode and layout before opening training logs. LeRobot converts time offsets into tick offsets, clamps indices to episode bounds, and marks padded slots with `action_is_pad`. If an episode ends at frame 79, a window starting at 77 loads `[77, 78, 79, 79]` with mask `[False, False, False, True]`. In the CPU check on the pinned data, episode 0 ended at frame 160. The last sample showed four copies of `[164, 355]` and mask `[False, True, True, True]`. The [training lecture](/notes/lerobot-training/) traces how ACT uses this mask. [Tagged offset and padding implementation](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/datasets/lerobot_dataset.py)

## Choose a split that tests the intended generalization

The last 20 PushT episodes are an example holdout. A random row split can leak even if every input row appears only once. Each sample receives multiple labels from neighboring ticks.

```text
One episode                  tick:    38   39   40   41   42
Window at 38 assigned to train       a38  a39  a40  a41
Window at 39 assigned to holdout           a39  a40  a41  a42
                                           |----shared----|
```

Three of the four labels of the holdout example already appear in training. Keep episodes together. If IDs 0–7 share one collection session, 8–15 share another, and 16–19 come from a third camera mount, holding out 16–19 tests transfer to that mount. To test repeat resets with the same mount, collect more than one session under that mount and hold out whole sessions. Record the original IDs and the claim each split is designed to test.

Even disjoint splits can leak information through fitted transformations. If the training x-targets are 100 and 200 and the holdout contains 500, the training mean is 150. Pooling all three gives 266.7, so the holdout changes every standardized training target. Materialize a training-only dataset for a genuine offline experiment and use its statistics on both splits. In this release, `episodes=[...]` restricts examples while metadata statistics can still describe the parent dataset. The tagged `split_dataset` helper aggregates statistics from the chosen episodes and reindexes their IDs. Keep the original split manifest. [Tagged dataset split implementation](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/datasets/dataset_tools.py)

## Exercises

### Debug a one-tick join

A recorder measured x = 200 at 0.2 s and then sent x-target 230. At 0.3 s the state was 212 and the target changed to 250. An export placed `(212, 230)` on the first row. Fix the pair and explain why the timestamp audit could still pass.

<details>
<summary>Solution</summary>
<p>The rows should be (200, 230) at 0.2 s and (212, 250) at 0.3 s. The faulty export used the result of the first command as its input. Regular timestamps can be regenerated after the incorrect join. Inspect the original capture and command stamps around a known target change, then fix the join upstream.</p>
</details>

### Design a holdout for a new camera pose

Two operators recorded on both camera mounts A and B. Which episodes go into holdout if you want to test whether a policy trained on A works on B? Should the holdout have its own normalizer?

<details>
<summary>Solution</summary>
<p>Keep every B episode together in holdout. Fit observation and action statistics with the A training episodes and apply those same transforms to B. Record original IDs and operator counts in each group. If you tune repeatedly on B, reserve another group for the final transfer claim.</p>
</details>

## Common misconceptions

- **A Parquet file is one episode.** Episode metadata addresses ranges within shared shards.
- **Matching shapes establish semantics.** Agent position and target position both have two coordinates. Check roles, units and timing independently.
- **Every repeated target is padding.** A demonstrator may hold a target for several ticks. Use the loader's boundary mask to identify synthetic slots.

## Summary

An episode is a causal trace through a control loop. Audit row structure, inspect a decoded window, and preserve the original IDs and statistics behind your split. Carry the same observation-before-action convention into [recording](/notes/lerobot-recording/) and the [tabletop capstone](/notes/capstone-tabletop/).
