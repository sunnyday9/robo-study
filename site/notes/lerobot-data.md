---
title: Read a robot learning dataset
topic: LeRobot
order: "30"
description: Inspect recorded observations and commands, audit their timing, and split by episode.
prerequisites: Python and basic supervised learning
minutes: 35
---

## Read an episode as a trajectory

LeRobot is a toolkit for recording, storing, training on, and evaluating robot learning data. PushT, the example used in this track, is a separate simulator. A circle pushes a T-shaped object toward a goal. The public demonstrations let you study a manipulation problem without starting a simulator or connecting a robot. The track uses LeRobot **v0.4.3** and the PushT dataset’s **v3.0** tag. [LeRobot release](https://github.com/huggingface/lerobot/releases/tag/v0.4.3) · [PushT dataset metadata](https://huggingface.co/datasets/lerobot/pusht/blob/b1c3ecbae7f244acc039a3dbc255a00dad1372b9/meta/info.json)

An episode begins at a reset and ends at a task outcome or collection cutoff. Think of row `t` as a snapshot of what the demonstrator could sense, paired with the command it issued from that snapshot. Stepping the controller with that command produces the next observation. Teaching a policy with the image *after* the command gives it information that would be unavailable at decision time.

![Two PushT episodes shown side by side. Each row pairs a pre-command observation with the command at that tick. The timestamp resets in the second episode, which stays entirely in the held-out split.](/assets/lerobot-episode-timeline.svg)

| Field | How to interpret it in PushT |
| --- | --- |
| `observation.image` | RGB view. The dataset stores frames in video and declares their shape as height × width × channels. |
| `observation.state` | Measured agent position, two coordinates. |
| `action` | Commanded target position, two coordinates in the simulator’s 512-unit workspace. Equal shape does not imply equal meaning. |
| `episode_index`, `frame_index`, `timestamp` | Episode ID, episode-local step and episode-relative time in seconds. At 10 Hz, one frame tick is 0.1 s. |
| `index`, `task_index` | Global row index and a key into task metadata. |

Version 3 stores many episodes in shared Parquet and video shards. Episode metadata locates each trajectory’s ranges inside those files. Video time can therefore include a shard offset even when the row timestamp starts at zero. Inspect the feature schema and decode through the dataset loader when you need synchronized images. [Tagged dataset implementation](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/datasets/lerobot_dataset.py) · [PushT action and observation spaces](https://github.com/huggingface/gym-pusht#description)

## Lab · audit a shard offline

Install PyArrow with `python -m pip install pyarrow` in a virtual environment. Download [the pinned PushT Parquet shard](https://huggingface.co/datasets/lerobot/pusht/resolve/b1c3ecbae7f244acc039a3dbc255a00dad1372b9/data/chunk-000/file-000.parquet) as `file-000.parquet`. The runnable Python below reads only that local file. It needs neither PyTorch nor video decoding.

```python
from collections import defaultdict
from math import isclose, isfinite

import pyarrow.parquet as pq

columns = ["episode_index", "frame_index", "timestamp",
           "observation.state", "action"]
episodes = defaultdict(list)
for row in pq.read_table("file-000.parquet", columns=columns).to_pylist():
    episodes[row["episode_index"]].append(row)

for rows in episodes.values():
    for tick, row in enumerate(rows):
        assert row["frame_index"] == tick
        assert isclose(row["timestamp"], tick / 10, abs_tol=1e-4)
        for key in ("observation.state", "action"):
            assert len(row[key]) == 2 and all(map(isfinite, row[key]))

ids = sorted(episodes)
train_ids, held_out_ids = ids[:-20], ids[-20:]
assert set(train_ids).isdisjoint(held_out_ids)
print(len(ids), sum(map(len, episodes.values())))
print(episodes[ids[0]][0])
```

**Checkpoint.** Expect 206 episodes and 25,650 rows. Episode 0 starts at frame 0 and time 0 with measured position `[222, 97]` and target `[233, 71]`. Compare the first five state and action pairs in one episode. If a check fails, inspect the episode ID and neighboring rows before sorting or repairing anything. An apparently regular software timestamp can still hide stale camera frames or delayed commands.

Treat the last 20 IDs as an example holdout. For your own data, group by collection session or scene when a reset sequence, operator, or camera viewpoint repeats. Keep complete groups out of training, fit dataset-dependent normalizers on training data, and build action windows within episode boundaries.

## Self-check

Why can a random row split make held-out action error look better?

<details>
<summary>Check your answer</summary>
<p>Adjacent rows often depict almost the same scene and share actions in overlapping target windows. Random row splitting gives training near-duplicates of holdout examples. Episode or session grouping tests a more meaningful kind of generalization.</p>
</details>

Use these checks on the logs from [recording demonstrations](/notes/lerobot-recording/) and on the replay traces in the [tabletop capstone](/notes/capstone-tabletop/).
