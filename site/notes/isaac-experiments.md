---
title: Run repeatable simulation and data experiments
topic: Isaac Sim
order: "23"
description: Control stepping and capture cadence, then separate perception labels from action demonstrations and evaluate each on its own terms.
prerequisites: The Franka pick-and-place baseline and basic Python logging
minutes: 50
---

## Decide what happens on each tick

The **physics timestep** controls how often the solver advances joint motion and contact. The **control period** determines when the policy sees a new observation and chooses an action. The **render schedule** controls when images are drawn. A sensor can have its own capture cadence. Isaac Sim can advance several physics steps per rendered frame. For experiments, schedule events on simulation time and measure throughput in wall time. [NVIDIA physics and rendering fundamentals](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/physics/simulation_fundamentals.html)

![Illustrative simulation timeline with a physics step every tick, a render every two ticks, a new held command every four ticks, and a camera sample every eight ticks.](/assets/isaac-cadence.svg)

At 120 physics steps per simulated second, four steps per control interval give 30 decisions per second. If the camera runs at 15 Hz, every other decision needs to reuse the latest available frame or follow another explicitly chosen sampling rule. A reused frame keeps its capture timestamp. Joining a future image to an earlier action leaks information the policy could never see at deployment.

| Dataset | Unit of data | What it can answer |
| --- | --- | --- |
| Synthetic perception data | RGB or depth plus rendered labels, such as boxes or segmentation | Can the model locate or segment the cube under varied lighting? |
| Action demonstration | Ordered observation and command pairs with episode boundaries | Can the learner predict the demonstrator's next command from available observations? |

Replicator can write RGB and ground-truth labels from a render product. Run NVIDIA's **Data Capture: BasicWriter** example and inspect one image and its corresponding box output in `_out_basic_writer`. The standalone command below runs from the installation directory. [NVIDIA Replicator example](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/replicator_tutorials/tutorial_replicator_getting_started.html#data-capture-basicwriter)

```bash
./python.sh standalone_examples/api/isaacsim.replicator.examples/sdg_getting_started_01.py
```

## Lab · repeat a run and define an action log

1. Run this included Franka test twice in fresh processes. Save the logs and exit statuses. The 6.1.0 example defines a step budget in test mode and checks that the cube lifts and settles within tolerance. **Headless** removes the app window. GPU rendering can still run for camera experiments. [Tagged Franka test source](https://github.com/isaac-sim/IsaacSim/blob/v6.1.0/source/standalone_examples/api/isaacsim.robot_motion.examples/manipulation/pick_place.py) · [NVIDIA headless performance notes](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/reference_material/sim_performance_optimization_handbook.html)

   ```bash
   ./python.sh standalone_examples/api/isaacsim.robot_motion.examples/manipulation/pick_place.py --robot franka --headless --test
   ```

2. Instrument a learner-owned copy of the example at the point where the controller produces a command. Use the following **illustrative pseudocode** to plan the log. Record the action actually sent to the simulated robot, including the gripper command. Write down the joint order, units, action mode, and coordinate frames.

   ```text
   at each controller update:
       t = current simulation time
       obs = measured joints and latest available camera frame at or before t
       action = expert command from this update
       write episode ID, step index, t, observation, frame capture time, action
   at episode end:
       write termination reason and the measured placement outcome
   ```

3. Compare repeated runs with the same scene, initial state, simulator and physics backend, driver, time settings, and random seeds where applicable. Check step counts, peak lift, final placement error, and outcome against tolerances you declared before comparing runs. Then change one factor, such as the cube's starting pose, and repeat. A fixed seed alone gives no guarantee of bitwise-identical contacts or images across devices and versions.

**Checkpoint.** Verify increasing decision times within each episode, correct action dimension and units, and camera timestamps at or before their decisions. If captures lag behind state, log and inspect the sample age. If images are missing at shutdown, drain the writer. Replicator provides `rep.orchestrator.wait_until_complete()` for synchronous scripts. [NVIDIA capture and writer lifecycle](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/replicator_tutorials/tutorial_replicator_getting_started.html#wait-until-complete)

## Carry the evidence into the capstone

In the [tabletop capstone](/notes/capstone-tabletop/), replay a recorded episode to validate the reader and data contract, produce fresh simulated pick-and-place demonstrations, then evaluate imitation offline on held-out **episodes**. If using LeRobot, explicitly adapt and validate the episode schema and action semantics for that workflow. Report held-out action error as an offline result. Closed-loop rollout success requires its own experiment, and real hardware adds calibration error, latency, contact variability, and actuator limits.

## Self-check

Why can a perfect offline action score coexist with a failed closed-loop simulated grasp?

<details>
<summary>Check your answer</summary>
<p>Offline scoring supplies recorded observations. In a rollout, actions change the next observation. Small errors or timing shifts can accumulate and drive the robot into states that the demonstrations did not cover.</p>
</details>
