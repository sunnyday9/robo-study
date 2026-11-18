---
title: Run repeatable simulation and data experiments
topic: Isaac Sim
order: "084"
description: Control stepping and capture cadence, then separate perception labels from action demonstrations and evaluate each on its own terms.
prerequisites: The Franka pick-and-place baseline and basic Python logging
minutes: 50
---

## Decide what you want to learn from a run

The Franka demo picked up a cube once. Before collecting a hundred episodes, ask a question that a batch of runs can answer. For example, does moving the cube 2 cm sideways from the nominal spawn reduce settled placement success with the same controller? A repeat at the nominal spawn tells you whether the baseline is stable enough to interpret a change. A failed run with a phase trace tells you more about what to fix than a successful video alone.

For this lab, aim for two artifacts. First, a trial record for every requested run, including failures and exit statuses. Second, an observation–action contract that a separate reader can audit around a contact event. These answer different questions: whether the task completed and whether you captured information the learner could actually have used. Keep both even when an experiment exposes a bug.

## Decide what happens on each tick

The **physics timestep** controls how often the solver advances joint motion and contact. The **control period** determines when the policy sees a new observation and chooses an action. The **render schedule** controls when images are drawn. A sensor can have its own capture cadence. Isaac Sim can advance several physics steps per rendered frame. For experiments, schedule events on simulation time and measure throughput in wall time. [NVIDIA physics and rendering fundamentals](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/physics/simulation_fundamentals.html)

![Illustrative simulation timeline with a physics step every tick, a render every two ticks, a new held command every four ticks, and a camera sample every eight ticks.](/assets/isaac-cadence.svg)

At 120 physics steps per simulated second, four steps per control interval give 30 decisions per second. If the camera runs at 15 Hz, every other decision needs to reuse the latest available frame or follow another explicitly chosen sampling rule. A reused frame keeps its capture timestamp. Joining a future image to an earlier action leaks information the policy could never see at deployment.

Read the diagram at tick 4, or 33.3 ms. The controller samples joints and picks action 1 before the next physics interval. The only camera capture so far is at tick 0, so action 1 can use that image if it has arrived and your age budget allows 33.3 ms of staleness. At tick 8 the new capture and the control update share a nominal time. Use the new image only if it has become available before that decision. For asynchronous sensors, acquisition time and availability order are both needed. If the tick-8 image arrives just after the decision, action 2 may use an older frame or record it as missing. These cadences illustrate a design, separate from the stock Franka test's nominal 60 Hz physics step.

Holding an action for four physics steps lets you change control cadence without coarsening contact integration. It also gives the robot time to move before the next observation can correct a deviation. Updating the policy only when a frame arrives makes fusion easier to reason about, but ties feedback to capture rate and jitter. Reusing frame data at each faster control update preserves a steady control period while requiring an explicit age limit and missing-image behavior. For a dataset, record which strategy generated the demonstrations. If each decision must have a unique image for the downstream reader, schedule decisions accordingly or design an explicit association instead of cloning rows and inventing timestamps.

| Dataset | Unit of data | What it can answer |
| --- | --- | --- |
| Synthetic perception data | RGB or depth plus rendered labels, such as boxes or segmentation | Can the model locate or segment the cube under varied lighting? |
| Action demonstration | Ordered observation and command pairs with episode boundaries | Can the learner predict the demonstrator's next command from available observations? |

Replicator can write RGB and ground-truth labels from a render product. Run NVIDIA's **Data Capture: BasicWriter** example and inspect one image and its corresponding box output in `_out_basic_writer`. The standalone command below runs from the installation directory. [NVIDIA Replicator example](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/replicator_tutorials/tutorial_replicator_getting_started.html#data-capture-basicwriter)

```bash
./python.sh standalone_examples/api/isaacsim.replicator.examples/sdg_getting_started_01.py
```

Inspect whether the box encloses the intended visible object and whether image and annotation filenames identify the same capture. This is supervision from rendered scene labels. An imitation sample has a different dependency: after reading measured state and eligible images, the expert computes a command and the simulator applies it. The block pose can serve as privileged expert input or an evaluation label. If a deployed policy sees only RGB and joints, keep that pose out of its input features.

## Lab · repeat a run and define an action log

1. Run this included Franka test twice in fresh processes. Save the logs and exit statuses. The 6.1.0 example defines a step budget in test mode and checks that the cube lifts and settles within tolerance. **Headless** removes the app window. GPU rendering can still run for camera experiments. [Tagged Franka test source](https://github.com/isaac-sim/IsaacSim/blob/v6.1.0/source/standalone_examples/api/isaacsim.robot_motion.examples/manipulation/pick_place.py) · [NVIDIA headless performance notes](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/reference_material/sim_performance_optimization_handbook.html)

   ```bash
   logs=$(mktemp -d) || exit 1
   printf 'Logs in %s\n' "$logs"
   for trial in 1 2; do
     if timeout --kill-after=15s 300s ./python.sh \
         standalone_examples/api/isaacsim.robot_motion.examples/manipulation/pick_place.py \
         --robot franka --headless --test > "$logs/$trial.log" 2>&1; then
       status=0
     else
       status=$?
     fi
     printf '%s\n' "$status" > "$logs/$trial.exit"
   done
   ```

   Expect status zero and `PASS: franka pick/place completed with a settled placement.` for a successful run. The Bash example uses a five-minute wall budget. Choose a budget that allows startup on your host before running the batch. A wall timeout catches a stalled process even when its simulation step counter never advances.

2. Instrument a learner-owned copy of the example at the point where the controller produces a command. Use the following **illustrative pseudocode** to plan the log. Record the action actually sent to the simulated robot, including the gripper command. Write down the joint order, units, action mode, and coordinate frames.

   ```text
   at each controller update:
       t = current simulation time
       obs = read measured joints and an eligible, already available frame
       action = expert command from this update
       submit action and record command time and applied values
       log episode ID, step index, t, observation, capture time and command
   at episode end:
       write termination reason and the measured placement outcome
   ```

   The stock script has no camera capture. Log the measured state passed to `controller.forward` and the targets submitted via `scenario.apply_robot_state`. Use named joints and record command mode and units, including linear travel for prismatic fingers. For a camera, keep stream ID, frame, calibration, encoding, and shape. Timestamp state and capture in the same simulation domain. The sample's `controller_time` advances by a nominal timestep per controller update, so check its relation to sensor stamps before using it for alignment. Start a new episode ID on reset and retain source stamps alongside episode-relative nanoseconds.

3. Compare repeated runs with the same scene, initial state, simulator and physics backend, driver, time settings, and random seeds where applicable. Check step counts, peak lift, final placement error, and outcome against tolerances you declared before comparing runs. Then change one factor, such as the cube's starting pose, and repeat. A fixed seed alone gives no guarantee of bitwise-identical contacts or images across devices and versions.

**Checkpoint.** Verify increasing decision times within each episode, correct action dimension and units, and camera timestamps at or before their decisions. If captures lag behind state, log and inspect the sample age. If images are missing at shutdown, drain the writer. Replicator provides `rep.orchestrator.wait_until_complete()` for synchronous scripts. [NVIDIA capture and writer lifecycle](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/replicator_tutorials/tutorial_replicator_getting_started.html#wait-until-complete)

## Test the observation contract before collecting

This Python-only example models a single stream in one episode. Its event sequence records the order of frame delivery and observation reads without subtracting wall time from simulation time.

```text
Reader event       1               3              4               5
                  frame 0       decision       frame 1         decision
                  arrives       66.7 ms        arrives         100.0 ms
Capture stamp      0 ms                        66.7 ms
Selected frame                  missing                        frame 1
```

At event 3, frame 0 exceeds the 40 ms age limit and frame 1 has yet to arrive. At event 5, frame 1 is available and about 33 ms old. The last assertion checks an intentionally inconsistent future stamp.

```python
def select_frame(frames, decision_ns, decision_seq, max_age_ns):
    eligible = (
        frame
        for frame in frames
        if frame["available_seq"] < decision_seq
        and 0 <= decision_ns - frame["capture_ns"] <= max_age_ns
    )
    return max(eligible, key=lambda frame: frame["capture_ns"], default=None)


frames = [
    {"id": 0, "capture_ns": 0, "available_seq": 1},
    {"id": 1, "capture_ns": 66_666_667, "available_seq": 4},
    {"id": 2, "capture_ns": 133_333_333, "available_seq": 6},
]
assert select_frame(frames, 66_666_667, 3, 40_000_000) is None
assert select_frame(frames, 100_000_000, 5, 40_000_000)["id"] == 1
# Deliberately inconsistent trace: a future-stamped frame is already queued.
assert select_frame(frames, 100_000_000, 7, 40_000_000)["id"] == 1
print("OK: frame availability and age gates")
```

The expected output is the printed line after the assertions. Change only frame 1's availability from event 4 to event 2. Predict that the first assertion fails because an image with the same capture time now qualifies. Replace that assertion with an ID check to confirm the expected selection, then restore the original fixture. In a real episode, a missing image should stay visible in the trace so you can evaluate the effect of a wait, fallback, or dropped decision. The [capstone CPU validator](/notes/capstone-tabletop/) checks a related CSV contract. It does not inspect image delivery order or contents.

## Run a paired comparison and debug the first divergence

After the smoke runs, make a trial list with nominal and +0.02 m cube Y offsets. Derive the pick goal from the changed spawn to test geometry and reach with a correctly specified grasp. Keep the place region, step budget, observation mode, physics settings, and controller fixed. To include variations in initial state, generate them in advance and use the same underlying cases in both conditions. Repeated launches of a fixed scene probe repeatability on your stack.

Count all predeclared runs in the denominator and report outcomes by condition. For example, an illustrative batch gives 10/10 successful nominal trials and 7/10 shifted trials, with two missed lifts and one settle timeout. The 30 percentage-point difference describes those trials. A small set of nearby poses gives weak evidence about a broader workspace. Keep a manifest with the scene and asset revision, launch options, start state, seed where used, simulator and driver, phase trace, maximum lift, final XY error, settling result, and failure reason. Finite controller and wall-time budgets distinguish slow trials from hangs. The reference success checks apply to the object after retreat, so report arm completion separately.

Compare a passing and failing trial at the first divergent phase. Suppose the shifted trials descend accurately and can lift the block, but two drop it before release. Test finger contacts and relative motion during transfer rather than exporting more runs. If drops cluster where an observation is stale, replay the nearby rows and inspect frame age and the ordering of state, command and physics. A one-row label shift can look plausible during slow motion and become obvious as the gripper closes. Make a single targeted change, rerun the same trial list, and preserve the earlier result so there is evidence for the change.

## Carry the evidence into the capstone

In the tabletop capstone, replay a recorded episode to validate the reader and data contract. For an imitation study, split by **episode** or scene group before fitting normalization, and reserve separate reset cases for rollout evaluation. An offline score measures action error on recorded observations. A closed-loop score measures task success when commands change future observations. Report both separately if both are run. Compared with simulation, hardware also introduces calibration error, latency, contact variability, and actuator limits. [Tabletop capstone](/notes/capstone-tabletop/)

The course's LeRobot 0.4.3 and Python 3.12 lab uses PushT. Franka pick-and-place has different observations, actuators, and execution semantics. Keep the demonstrations and evaluation on their respective environments unless you implement and validate an explicit adapter for schema, units, frame and action conventions, control timing, and reset behavior. A compatible file layout alone cannot turn a PushT position command into a Franka joint target. [LeRobot data](/notes/lerobot-data/) · [LeRobot training lab](/notes/lerobot-training/)

## Exercises and solutions

Why can a perfect offline action score coexist with a failed closed-loop simulated grasp?

<details>
<summary>Check your answer</summary>
<p>Offline scoring supplies recorded observations. In a rollout, actions change the next observation. Small errors or timing shifts can accumulate and drive the robot into states that the demonstrations did not cover.</p>
</details>

You double physics from 120 Hz to 240 Hz and keep the old divisors of 4 for control and 8 for the camera. You intended to study contact integration alone. What has changed, and how would you repair the experiment?

<details>
<summary>Check your answer</summary>
<p>The controller now runs at 60 Hz and the requested camera schedule is 30 Hz, assuming renderer capacity. Those were 30 and 15 Hz originally. Use intervals of 8 physics ticks for control and 16 for capture, keep the same simulated episode duration, and check that the render and delivery path actually supplies images at the intended cadence. Then compare the paired trials.</p>
</details>

## Common misconceptions

- **A fixed seed makes a run portable and deterministic.** Library versions, solver backend, scheduling and hardware still affect results. Save the configuration and declare tolerances.
- **Every rendered image is a demonstration.** Perception labels supervise scene interpretation. Imitation requires a time-ordered observation and the command issued from it.
- **More successful episodes will fix a low rollout score.** Inspect action alignment and failures around contact before growing a dataset that might contain the same error.

## Summary

Control physics, decisions, and capture as separate schedules on one simulation clock. Pair observations with commands they could inform, test that pairing with a small fixture, and record failures as carefully as successes. A matched trial list makes one change interpretable. Keep the resulting evidence tied to the task and execution path that produced it.
