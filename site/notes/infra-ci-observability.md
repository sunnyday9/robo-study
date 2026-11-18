---
title: Test robotics software and diagnose failures
topic: Infrastructure
order: "103"
description: Give each CI job a clear claim and collect evidence that locates failures across replay, simulation, and evaluation.
prerequisites: Know how ROS replay and container inputs are scoped
minutes: 50
---

## Match the job to the claim

Someone merges a preprocessing change after CI passes. That night's Isaac job times out, and the LeRobot result appears to improve because fewer episodes made it through scoring. A single green badge hides both problems. Give each job one claim with an input, an observable output, and a failure condition. You want a fast job that can catch a real contract violation on every change, plus enough evidence from slower jobs to localize the first failure without rerunning everything.

Continuous integration (CI) runs checks under specified conditions. Put fast, small checks on CPU runners for each change. Use a separate tagged GPU lane for features that need a supported GPU and a known driver. Keep every job away from actuator networks. A green CPU job gives evidence about its inputs and assertions. Track GPU results independently, with explicit pass, fail, or skipped status.

| Lane | Suggested checks | Evidence to save |
| --- | --- | --- |
| CPU on each change | Validate schemas, monotonic episode timestamps, frame and action dimensions, and split disjointness. Replay a tiny fixture locally on a ROS-equipped CPU runner. | Exit status, fixture digest, test report, topic counts, and timing bounds checked. |
| Tagged Isaac GPU | On a trusted run, launch Isaac Sim 6.1.0 headless, load a pinned stage, run fixed steps, and check one sensor output and the scripted controller's outcome. | Runner manifest, image digest, render and physics logs, seed, and success count over all planned trials. |
| LeRobot offline eval | Use LeRobot v0.4.3 and Python 3.12. Decode held-out episodes and evaluate a pinned checkpoint on CPU when the policy permits or on a compatible GPU. | Dataset revision, split, checkpoint and preprocessing hashes, error units, and counts of episodes and scored actions. |

An illustrative GitHub Actions job uses the routing field `runs-on: [self-hosted, linux, x64, gpu, rtx]`. Custom labels such as `gpu` and `rtx` route jobs only when you assign them to suitable runners. Preflight the actual GPU and driver before opening a stage. Run trusted revisions on isolated GPU runners with job timeouts. Untrusted pull requests belong on isolated hosted runners. [GitHub runner labels](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow), [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use).

Order checks by cost and diagnostic value. A malformed fixture should fail in seconds. A replay test adds evidence about topic types, clocks, and delivery. A renderer-and-controller test adds evidence about the pinned scene and simulator. A separate LeRobot v0.4.3/Python 3.12 evaluation can decode examples and score the PushT policy under the declared conditions. An Isaac Franka pass tells you nothing about that policy's action space. Integration across these systems requires a validated adapter. Keep observation before action and select one simulation clock where replay or simulation supplies ROS time.

## Run a scoped fixture check in CI

The following is a complete teaching workflow for GitHub.com. Save it as `.github/workflows/infra-trace.yml` in a practice repository that has the existing [capstone validator](/assets/labs/check_trace.py) and [teaching trace](/assets/labs/tabletop-trace.csv) under `site/assets/labs/`. It uses an Ubuntu 24.04 hosted runner with Python 3.12, takes no secrets, and requires no ROS or GPU. For team workflows, use reviewed full commit SHAs for third-party and first-party action dependencies. The major tags here make the example easier to read. [Hosted runner labels](https://docs.github.com/en/actions/reference/runners/github-hosted-runners), [setup-python](https://github.com/actions/setup-python), [upload-artifact](https://github.com/actions/upload-artifact).

```yaml
name: Trace fixture
on: [pull_request, push]
permissions:
  contents: read
jobs:
  trace-contract:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    defaults:
      run:
        shell: bash
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - name: Verify valid and over-budget pairings
        run: |
          mkdir -p evidence
          cd site/assets/labs
          out=../../../evidence
          { git rev-parse HEAD; python --version;
            sha256sum check_trace.py tabletop-trace.csv; } > "$out/inputs.txt"
          python check_trace.py tabletop-trace.csv 2>&1 | tee "$out/baseline.log"
          grep -Fx 'OK: 6 rows across 2 episodes' "$out/baseline.log"
          status=0
          python check_trace.py tabletop-trace.csv --max-skew-ns 1000000 \
            > "$out/tight-budget.log" 2>&1 || status=$?
          cat "$out/tight-budget.log"
          test "$status" -eq 1
          grep -Fx 'FAIL: line 3: observation-to-command skew outside budget' \
            "$out/tight-budget.log"
      - name: Save fixture evidence
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: trace-contract
          path: evidence/
          retention-days: 7
```

Design the negative case alongside the positive one. The fixture's largest skew is 2 ms. With the default 10 ms budget the expected count is six rows across two episodes. Tighten the budget to 1 ms and the validator should exit 1 with the specified diagnostic. A missing Python file also exits nonzero. Requiring the expected reason prevents CI from mistaking infrastructure errors for successful rejection. GitHub's explicit Bash shell applies pipeline failure handling so `tee` preserves the log without hiding a failing validator. Download the evidence when it fails and reproduce against the recorded fixture and commit before editing the assertion. [Workflow shell behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

Run the two Python invocations locally first. Once the workflow passes, deliberately move the second command stamp in a scratch copy one nanosecond before its observation and run the baseline check on that copy. Expect an ordering or skew failure. Restore the fixture and rerun the check. If you want to make frame alignment a release claim, add a separate test that pairs visible movement and action in a tiny replay. The CSV gate sees IDs and stamps and cannot tell whether the selected image matches the row.

## Collect evidence that narrows the fault

Use **logs** for discrete events such as a missing texture or an incompatible subscriber. Give each record a stage, run ID, episode ID where applicable, and a timestamp with its clock source. Use **metrics** for counts and distributions such as dropped frames, peak VRAM, and p95 decode latency. Put denominator and units next to each result. Use **traces** to follow one sample across capture, transfer, decode, and evaluation. Correlate spans using a sample or trace ID. Use monotonic elapsed time within a process and account for clock offsets when comparing across hosts. [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/).

Save the resolved launch arguments, commit, host manifest, versions, artifact hashes, seeds, and pass criteria on both successful and failed runs. Compare with the last passing run using one changed input at a time. Pinning a seed improves repeatability within a setup. Across platforms and devices, choose a tolerance for numeric checks and keep discrete invariants exact. [PyTorch reproducibility](https://docs.pytorch.org/docs/2.7/notes/randomness.html).

Suppose you have a 33 ms processing budget and one illustrative sample from a local replay process. Use a monotonic timer for elapsed work in that process. Preserve the source acquisition stamp separately for alignment.

```text
 episode B / frame 17        elapsed wall time from arrival
 arrive        decode starts  decode ends        command emitted
   0 ms ------------ 19 ms ------ 27 ms -------------- 41 ms
          queue wait          decode           inference + send
           19 ms               8 ms                  14 ms
                                            ^
                                       budget at 33 ms
```

This sample misses the budget by 8 ms. Queue wait is its longest interval. Optimizing only the 8 ms decode by half would reach 37 ms and still miss. Measure how often each interval dominates across many samples. A smaller queue can reduce stale frames at the cost of drops. A faster consumer can preserve frames but may need more compute. Repeat the same replay twice at the same rate to estimate run variation, then change one factor, such as queue depth. Compare latency, deadline misses, and drops together. If the processes run on different hosts, join by episode and frame or a trace ID and use local span durations until you have bounded clock offset. A ROS simulation clock can pause or jump and is appropriate for sample semantics, while a monotonic timer is appropriate for elapsed wall time.

Start with application spans around enqueue, decode, inference, and action emission. On a Linux Jazzy host with `ros2_tracing` and LTTng already configured, start `ros2 trace --session-name infra-replay --list`, press Enter to start capture, then launch the tiny replay in another terminal and stop the trace after the run. Starting before node initialization preserves the metadata used to map events to nodes. Compare callback start and end times and join them to application events where the instrumentation provides a shared ID. The ROS trace alone may omit GPU work or time waiting outside instrumented callbacks. Use a small trace window and compare the same workload with tracing disabled to check perturbation. [Jazzy tracing tutorial](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Advanced/ROS2-Tracing-Trace-and-Analyze.rst).

## Report reliability with denominators

Define the run population and pass rule before launch. An illustrative suite plans 20 Franka resets. It succeeds on 15, fails the task on two, and times out on three. The result is **15/20**, with the timeouts still visible. Reporting 15/17 would reward the system for timing out. An offline loss can still improve on its scored subset, so report the count scored and how many could not be decoded. For a timing gate, define the population, units, and threshold in advance. For example, record how many commands among all scheduled frames meet the 33 ms budget, then report p95 among completed commands with a separate miss count for drops. Treat retries as new attempts and retain the original result and logs. If a noisy runner dominates variance, fix the environment or set an evidence-based bound before the timing check gates merges.

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

## Exercises

<details>
<summary>Self-check · CPU checks pass but the GPU job produces zero camera frames. Where do you start?</summary>
<p>Check the GPU probe and simulator startup logs, then stage asset resolution, simulation progress, camera configuration, and output permissions. A CPU schema check cannot establish that the renderer ran. Keep the GPU result failed or skipped according to what actually happened.</p>
</details>

<details>
<summary>Transfer · The queue drops 15 of 100 samples, and the rest all finish within the budget. Can this pass a 95% deadline target?</summary>
<p>No. The observed deadline success is 85/100 because a dropped sample produced no command by the deadline. Report 15 drops and the latency distribution for the 85 completions. Compare a larger queue and a faster consumer independently using the same ordered fixture and rate. Choose the variant that meets both the latency and completeness criteria.</p>
</details>

## Common misconceptions

- **“Green CI means the robot works.”** Each check supports only the claim exercised on its runner and fixture.
- **“A faster p95 proves the system improved.”** Inspect its population and the dropped or timed-out cases before concluding that more samples met the deadline.
- **“A log timestamp tells me how long inference took.”** Use a monotonic span around the work. Preserve source timestamps for observation and action alignment.

## Summary

Turn one data contract into a small positive and negative CI test. Save inputs and results on failure so you can reproduce it. For slower lanes, trace the first divergent sample, change the suspected cause in isolation, and report timing and success against predeclared populations.

For the [tabletop capstone](/notes/capstone-tabletop/), attach evidence in order from ROS replay through simulated pick-and-place to offline imitation evaluation. With no validated adapter, use a supported LeRobot dataset and report the offline result for that dataset. Offline action error measures agreement on recorded observations. Task completion requires a closed-loop rollout.
