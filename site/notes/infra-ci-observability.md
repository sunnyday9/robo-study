---
title: Test robotics software and diagnose failures
topic: Infrastructure
order: "43"
description: Give each CI job a clear claim and collect evidence that locates failures across replay, simulation, and evaluation.
prerequisites: Know how ROS replay and container inputs are scoped
minutes: 30
---

## Match the job to the claim

Continuous integration (CI) runs checks under specified conditions. Put fast, small checks on CPU runners for each change. Use a separate tagged GPU lane for features that need a supported GPU and a known driver. Keep every job away from actuator networks. A green CPU job gives evidence about its inputs and assertions. Track GPU results independently, with explicit pass, fail, or skipped status.

| Lane | Suggested checks | Evidence to save |
| --- | --- | --- |
| CPU on each change | Validate schemas, monotonic episode timestamps, frame and action dimensions, and split disjointness. Replay a tiny fixture locally on a ROS-equipped CPU runner. | Exit status, fixture digest, test report, topic counts, and timing bounds checked. |
| Tagged Isaac GPU | On a trusted run, launch Isaac Sim 6.1.0 headless, load a pinned stage, run fixed steps, and check one sensor output and the scripted controller's outcome. | Runner manifest, image digest, render and physics logs, seed, and success count over all planned trials. |
| LeRobot offline eval | Use LeRobot v0.4.3 and Python 3.12. Decode held-out episodes and evaluate a pinned checkpoint on CPU when the policy permits or on a compatible GPU. | Dataset revision, split, checkpoint and preprocessing hashes, error units, and counts of episodes and scored actions. |

An illustrative GitHub Actions job uses the routing field `runs-on: [self-hosted, linux, x64, gpu, rtx]`. Custom labels such as `gpu` and `rtx` route jobs only when you assign them to suitable runners. Preflight the actual GPU and driver before opening a stage. Run trusted revisions on isolated GPU runners with job timeouts. Untrusted pull requests belong on isolated hosted runners. [GitHub runner labels](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow), [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use).

## Collect evidence that narrows the fault

Use **logs** for discrete events such as a missing texture or an incompatible subscriber. Give each record a stage, run ID, episode ID where applicable, and a timestamp with its clock source. Use **metrics** for counts and distributions such as dropped frames, peak VRAM, and p95 decode latency. Put denominator and units next to each result. Use **traces** to follow one sample across capture, transfer, decode, and evaluation. Correlate spans using a sample or trace ID. Use monotonic elapsed time within a process and account for clock offsets when comparing across hosts. [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/).

Save the resolved launch arguments, commit, host manifest, versions, artifact hashes, seeds, and pass criteria on both successful and failed runs. Compare with the last passing run using one changed input at a time. Pinning a seed improves repeatability within a setup. Across platforms and devices, choose a tolerance for numeric checks and keep discrete invariants exact. [PyTorch reproducibility](https://docs.pytorch.org/docs/2.7/notes/randomness.html).

## Lab · Make a small failure explain itself

Run this Python 3 standard-library check in Bash. It uses two synthetic replay records and needs no ROS, ML packages, GPU, or robot. It checks timestamp order within one episode.

```bash
python3 - good <<'PY'
import json
import sys

run_id = "fixture-" + sys.argv[1]
stamps_ns = [0, 33_000_000 if sys.argv[1] == "good" else 0]
for sample, (previous, current) in enumerate(zip(stamps_ns, stamps_ns[1:]), 1):
    if current <= previous:
        print(json.dumps({
            "run_id": run_id, "stage": "replay", "episode": "demo-1",
            "sample": sample, "error": "non_increasing_timestamp",
            "previous_ns": previous, "current_ns": current,
        }), file=sys.stderr)
        raise SystemExit(1)
print(json.dumps({
    "run_id": run_id, "stage": "replay",
    "samples": len(stamps_ns), "status": "pass",
}))
PY
```

**Checkpoint.** The good case reports two samples and exits zero. Change the first line to `python3 - bad <<'PY'` and rerun the entire block. Expect exit 1 and identify the episode, zero-based sample index, and two timestamp values from stderr. Then sketch one trace linking that row to capture and decode so you can distinguish duplicate input data from a conversion error.

<details>
<summary>Self-check · CPU checks pass but the GPU job produces zero camera frames. Where do you start?</summary>
<p>Check the GPU probe and simulator startup logs, then stage asset resolution, simulation progress, camera configuration, and output permissions. A CPU schema check cannot establish that the renderer ran. Keep the GPU result failed or skipped according to what actually happened.</p>
</details>

For the [tabletop capstone](/notes/capstone-tabletop/), attach evidence in order from ROS replay through simulated pick-and-place to offline imitation evaluation. With no validated adapter, use a supported LeRobot dataset and report the offline result for that dataset. Offline action error measures agreement on recorded observations. Task completion requires a closed-loop rollout.
