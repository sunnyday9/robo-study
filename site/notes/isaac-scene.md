---
title: Build and inspect a simulated pick-and-place scene
topic: Isaac Sim
order: "21"
description: Trace a cube handoff from the USD stage through an articulated robot, a feedback controller, and contact physics.
prerequisites: A working Isaac Sim 6.1.0 workstation and basic coordinate frames
minutes: 45
---

## Start from the task contract

The arm can complete every commanded move while the block stays on the table. A pick-and-place developer needs to explain where those two histories diverge. Start with a fixed-base arm, two fingers, a single rigid cube, a flat support, and a target. Accept a trial when the cube lifts, reaches the target region, and settles there after release. Keep the arm and cube measurements separate from the start. The stock Franka example uses a ground plane as the support, so the surface sits at zero height. Its standalone target is a visible marker without a collider. Adding collision to the marker would change the task from placing on a flat surface to contacting another body.

## Compose the scene and verify what resolved

A USD layer stores authored opinions, such as a transform or a reference. A **stage** composes those opinions into the hierarchy consumed by the application. A **prim** is an address in that hierarchy. A reference brings an asset's prim subtree into the stage at a chosen path. The task layer can place the robot or override an attribute while the source asset remains shared. This separation lets you reproduce the same task with two versions of a robot asset and inspect exactly which version changed. It also introduces a debugging question: are you looking at the source attribute, a local override, or a value read from a live simulation?

```text
Franka USD asset -------- reference -----+
Task layer: spawn, support, target ------+--> composed stage
                                              /World/robot
                                              /World/Cube
                                              /World/PlaceTarget
                                              (plus static support)
                                                  |
                                                  v
         controller <-- measured arm state <-- PhysX step
              |                                ^      |
              +--- desired joint targets -----+      +--> cube pose
                                                           outcome gate
```

The paths shown are from the standalone example. A visible robot is evidence that geometry composed. The articulation and colliders must also be usable by the solver. The bottom of the diagram shows two separate outputs of a step. Measured tool and gripper state inform the next command, while the cube pose tells you whether the task is working. You can debug a missing reference while stopped and diagnose a drive or grasp only after stepping.

Check the stage's up axis and meters per unit before interpreting a transform as a distance. A referenced asset with different units needs a corrective transform or a compatible asset. Stage metadata alone does not rescale each referenced asset automatically. Inspect the cube's world pose, since translating a parent also moves a child with an unchanged local translation. In the Script Editor, with the example loaded, this small inspection runs against the composed stage. Use the actual path from the Stage panel if inspecting the interactive example. [OpenUSD fundamentals](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/omniverse_usd/open_usd.html) · [OpenUSD linear units](https://openusd.org/release/api/group___usd_geom_linear_units__group.html) · [Coordinate frames](/notes/coordinate-frames/)

```python
import omni.usd
from pxr import UsdGeom

stage = omni.usd.get_context().get_stage()
cube = stage.GetPrimAtPath("/World/Cube")
print("up:", UsdGeom.GetStageUpAxis(stage))
print("m/unit:", UsdGeom.GetStageMetersPerUnit(stage))
if not cube.IsValid() or not cube.IsDefined():
    raise RuntimeError("Find the composed cube path in the Stage panel")
world_pose = UsdGeom.XformCache().GetLocalToWorldTransform(cube)
print("composed cube center in stage units:", world_pose.ExtractTranslation())
```

Use this while stopped to inspect the authored starting pose. For motion traces, use the example's live rigid-body state reader. A defined prim at the robot mount is only the first check of a reference. Inspect expected descendant links and joints and any asset resolution errors if the subtree is incomplete.

| Part of the scene | What it contributes | What to inspect |
| --- | --- | --- |
| Arm articulation | Rigid links connected by joints and solved as a system | Fixed base, articulation root, joint names, axes, limits, and initial pose |
| Joint drives | Actuation that tracks position or velocity targets | Stiffness, damping, effort limits, and measured joint motion |
| Cube and support | A dynamic body resting on a static collider | Cube mass, collision shapes, contact friction, and a stable resting pose |
| Tool frame and controller | A reference pose for the gripper and a way to turn pose goals into joint targets | Tool-to-grasp offset, open and closed finger motion, and phase timeouts |

A **URDF** describes the robot's links, joints, inertial properties, and geometry. Isaac Sim's importer converts it to USD. For a different arm, enable `isaacsim.asset.importer.urdf` if needed and follow the release's **File → Import** tutorial. Inspect the USD after import. Verify the base constraint and command one joint gently in simulation, then watch which link moves and in which direction. Keep the packaged Franka USD and its matching controller configuration for the baseline below. [NVIDIA URDF workflow](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/importer_exporter/import_urdf.html)

## Design the phase transitions

Break the task into an approach above the cube, a descent with open fingers, a close, a lift, a transfer, a place descent, an open, and a retreat. Each phase needs an observable exit condition and a timeout. A fixed delay is easy to prototype, but if a joint is blocked the timer can send the gripper into the next phase in the wrong pose. Feedback can wait for adequate alignment and low speed. It needs sensible tolerances and a timeout so a stalled robot produces a diagnostic instead of waiting forever.

The 6.1.0 example uses a cuMotion RMPflow controller for arm motion and robot-specific gripper controllers. A goal refers to a grasp pose. The configured tool frame can be displaced from that grasp point. If a world-space goal concerns the fingertip midpoint, solve for the tool pose by composing the goal with the inverse of the tool-to-grasp transform. In a simple illustrative case with aligned frames and a grasp point 0.10 m below the tool along world Z, the tool should be at Z = 0.125 m to put the grasp point at Z = 0.025 m. In a rotated pose the offset rotates with the tool. Use the packaged configuration before attempting a new tool offset. Joint-drive targets still have to be followed under dynamics and contact. A reach error, drive tracking error, and slipping cube call for different repairs. [NVIDIA Franka example](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/examples/manipulation_franka_pick_place.html)

A single inverse-kinematics solve can answer whether one pose is reachable. It leaves open how to move there around obstacles. RMPflow produces motion commands from the current state, goal, and configured obstacle model. It can steer around a modeled obstacle locally, while a global planner is useful when the approach needs a substantial detour. Separately, the task state machine decides when to advance. Its default tool position and orientation tolerances are 0.015 m and 0.12 rad, held for at least 0.10 s. Grasp and release also check gripper completion. These thresholds concern the tool and fingers. The standalone task evaluates the cube separately. [NVIDIA RMPflow tutorial](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/cumotion/tutorial_rmpflow.html) · [Tagged controller source](https://github.com/isaac-sim/IsaacSim/blob/v6.1.0/source/extensions/isaacsim.robot_motion.examples/isaacsim/robot_motion/examples/manipulation/controllers/pick_place.py)

## Lab · inspect the Franka baseline

1. Open **Window → Examples → Robotics Examples → Manipulation → Franka Pick Place** and click **LOAD**. In the Stage panel, find the robot, cube, and support. Inspect the cube and support colliders with **Window → Simulation → Debug**, under **Collision Mesh Debug Visualization**. Compare the collision shape against the visible mesh. [NVIDIA Franka example](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/examples/manipulation_franka_pick_place.html) · [Collider visualization](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/physics/simulation_fundamentals.html)
2. Click **START PICK PLACE**. Track the sequence from approach and descent through close, lift, transfer, release, and retreat. RMPflow generates arm motion toward tool poses. The example's phase logic uses measured feedback to decide when motion is complete. Joint drives then act on the robot. Contact between the fingers and cube carries the cube.
3. Check that the cube remains near the target after the fingers open and retreat. Use the example's **RESET** and repeat. If you prefer a scripted run, this runnable Linux command launches the included example from the installation directory.

   ```bash
   ./python.sh standalone_examples/api/isaacsim.robot_motion.examples/manipulation/pick_place.py --robot franka
   ```

**Checkpoint.** In the standalone example a 5 cm cube starts at `(0.45, 0, 0.025)` m and moves toward `(0.45, 0.35, 0.025)` m. The 2.5 cm center height puts its bottom on the plane. The source checks that the center rises by at least 0.05 m. After controller completion it checks XY error ≤ 0.05 m, absolute Z error ≤ 0.03 m, linear speed ≤ 0.05 m/s, and angular speed ≤ 0.5 rad/s for 30 consecutive checks at the nominal 60 Hz step. A snapshot at release could pass the position check while the cube is still sliding. For example, a settled center at `(0.47, 0.31, 0.025)` is about 0.045 m from the target in XY and meets the position limits. It needs to pass the velocity and lift checks too. [NVIDIA's tagged example source](https://github.com/isaac-sim/IsaacSim/blob/v6.1.0/source/standalone_examples/api/isaacsim.robot_motion.examples/manipulation/pick_place.py)

## Trace the first phase that loses the cube

Create a learner-owned copy of the standalone script. Inside the update loop, insert this probe just before the existing `if previous_phase is not controller.phase:` block. The labels refer to the sampled state before the new target has affected a subsequent step. Logging transitions and occasional in-phase samples makes a short trace you can compare across runs. For a failure, also keep the exception and the last several samples.

```python
if previous_phase is not controller.phase or steps % 10 == 0:
    p, v, _ = _object_state(cube_prim)
    print(
        f"step={steps} t={controller_time:.3f} "
        f"{previous_phase.name}->{controller.phase.name} "
        f"cube={p.round(4).tolist()} speed={np.linalg.norm(v):.4f}",
        flush=True,
    )
```

Imagine these illustrative readings, sampled during each phase.

| Controller phase | Cube center Z | Cube Y | What to inspect next |
| --- | ---: | ---: | --- |
| `GRASP` | 0.025 m | 0.000 m | Is the grasp point centered and are both fingers making contact? |
| `LIFT` | 0.096 m | 0.002 m | The lift gate has already passed. Compare tool and cube motion from here. |
| `APPROACH_PLACE` | 0.027 m | 0.070 m | Cube height collapsed as the hand traveled. Inspect grip and contact through transfer. |
| `RETREAT` | 0.025 m | 0.083 m | The cube settled too far from the target. Changing the release pose alone cannot explain the earlier drop. |

Start by predicting the first symptom of a controlled fault. In the copied script, shift only the pick goal Y by +0.06 m, leaving the cube spawn and place goal unchanged. Make the edit in the first tuple passed to `_make_goal`, then rerun from a fresh process with the same configuration. The offset exceeds half the cube width. Expect an off-center descent, followed by a missed grasp or a failed phase. The exact outcome depends on geometry and motion. Compare against the stock trace at descent, close, and lift. If the hand reaches the shifted target and the cube stays at support height, the pose planner did what it was asked to do. Restore the known-good pick goal and rerun to test the explanation.

When the baseline itself fails, first classify the symptom. A cube dropping through the plane before the fingers arrive points toward rigid-body or collision configuration. A large tool-to-target error on descent calls for checking the goal frame, tool transform, obstacle model, and joint tracking. If tool placement is good but the trace shows loss during lift, inspect collision geometry, friction, contact and gripper effort before retuning the arm. After each edit, keep the successful baseline and add the smallest failing condition as a repeatable trial.

## Exercises and solutions

The gripper reaches the nominated place pose, opens, and retreats. What evidence would make the episode a success?

<details>
<summary>Check your answer</summary>
<p>Check that the cube lifted clear of the support and that its measured pose and velocity satisfy a placement and settling criterion after release. The arm's pose only establishes that the arm reached its target.</p>
</details>

The plane is replaced by a table with a top at Z = 0.72 m. You update the visual scene and the arm presses its open fingers against the tabletop during descent. Where should the 5 cm cube's center start, and what other changes have to agree?

<details>
<summary>Check your answer</summary>
<p>Use Z = 0.745 m for the resting center on that surface. Update spawn, pick and place goals, and the expected settled height in the same world frame. Verify the table collider independently, recompute the grasp and clearance poses with the tool offset, and check the fixed-base arm's reach and the controller's obstacle configuration before asking for a grasp.</p>
</details>

## Common misconceptions

- **The geometry I see is the collider.** The solver uses collision shapes, which can differ substantially from visible meshes. Inspect both.
- **A completed close confirms a grasp.** Finger state can satisfy a controller condition while the cube is off-center or slipping. The object's motion provides the evidence.
- **More stiffness fixes any missed target.** First separate an incorrect pose request from a physically unreachable or poorly tracked request.

## Summary

Compose the asset and task independently, then inspect the resulting prims and frames. Instrument the joint-command and cube-state boundaries before making changes. Work from the earliest phase where a measured quantity falls outside its expectation, and rerun the baseline after each isolated fix.

Use the plane-supported example as the manipulation baseline for the [tabletop capstone](/notes/capstone-tabletop/). For an elevated table, add a static collider and recompute the cube's spawn and goal heights relative to its top. Check reach from the arm's fixed base and include the table in the controller's obstacle model. Use the [bridge lab](/notes/isaac-ros-bridge/) to learn how an external program can interpret a simulated sensor stream.
