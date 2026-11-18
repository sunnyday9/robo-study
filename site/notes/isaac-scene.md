---
title: Build and inspect a simulated pick-and-place scene
topic: Isaac Sim
order: "21"
description: Trace a cube handoff from the USD stage through an articulated robot, a feedback controller, and contact physics.
prerequisites: A working Isaac Sim 6.1.0 workstation and basic coordinate frames
minutes: 45
---

## Start from the task contract

Our tabletop task has a fixed-base arm, a gripper, a single rigid cube, a flat support surface, and a destination. The stock Franka example uses a ground plane as the support surface. Treat it as a tabletop abstraction with the support at zero height. The goal is to lift the cube, carry it, and release it so it comes to rest near the target. The target can be a pose in software. A physical marker would add another collider to the scene.

In OpenUSD the **stage** is the composed scene. A **prim** is an addressable object in its hierarchy. `/World` is a common parent for robot and task prims. Referencing a robot USD mounts its hierarchy at a path in your stage while allowing the asset to remain reusable. Check the stage's units and up axis before comparing heights, and express the pick pose and placement target in the same frame. [OpenUSD fundamentals](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/omniverse_usd/open_usd.html) · [Coordinate frames](/notes/coordinate-frames/)

| Part of the scene | What it contributes | What to inspect |
| --- | --- | --- |
| Arm articulation | Rigid links connected by joints and solved as a system | Fixed base, articulation root, joint names, axes, limits, and initial pose |
| Joint drives | Actuation that tracks position or velocity targets | Stiffness, damping, effort limits, and measured joint motion |
| Cube and support | A dynamic body resting on a static collider | Cube mass, collision shapes, contact friction, and a stable resting pose |
| Tool frame and controller | A reference pose for the gripper and a way to turn pose goals into joint targets | Tool-to-grasp offset, open and closed finger motion, and phase timeouts |

A **URDF** describes the robot's links, joints, inertial properties, and geometry. Isaac Sim's importer converts it to USD. For a different arm, enable `isaacsim.asset.importer.urdf` if needed and follow the release's **File → Import** tutorial. Inspect the USD after import. Verify the base constraint and command one joint gently in simulation, then watch which link moves and in which direction. Keep the packaged Franka USD and its matching controller configuration for the baseline below. [NVIDIA URDF workflow](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/importer_exporter/import_urdf.html)

## Lab · inspect the Franka baseline

1. Open **Window → Examples → Robotics Examples → Manipulation → Franka Pick Place** and click **LOAD**. In the Stage panel, find the robot, cube, and support. Inspect the cube and support colliders with **Window → Simulation → Debug**, under **Collision Mesh Debug Visualization**. Compare the collision shape against the visible mesh. [NVIDIA Franka example](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/examples/manipulation_franka_pick_place.html) · [Collider visualization](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/physics/simulation_fundamentals.html)
2. Click **START PICK PLACE**. Track the sequence from approach and descent through close, lift, transfer, release, and retreat. RMPflow generates arm motion toward tool poses. The example's phase logic uses measured feedback to decide when motion is complete. Joint drives then act on the robot. Contact between the fingers and cube carries the cube.
3. Check that the cube remains near the target after the fingers open and retreat. Use the example's **RESET** and repeat. If you prefer a scripted run, this runnable Linux command launches the included example from the installation directory.

   ```bash
   ./python.sh standalone_examples/api/isaacsim.robot_motion.examples/manipulation/pick_place.py --robot franka
   ```

**Checkpoint.** Record the first phase that fails or, for a completed run, record the cube's lift and settled pose relative to the target. In the standalone example a 5 cm cube starts at `(0.45, 0, 0.025)` m and moves toward `(0.45, 0.35, 0.025)` m. The 2.5 cm center height puts the cube's bottom on the support. The example checks lift, placement error, and settling. A controller can reach the release pose even when the cube slips en route. [NVIDIA's tagged example source](https://github.com/isaac-sim/IsaacSim/blob/v6.1.0/source/standalone_examples/api/isaacsim.robot_motion.examples/manipulation/pick_place.py)

**Diagnostics.** A cube that falls through the support suggests a missing or mismatched collider. A hand that stops beside the cube suggests a frame or tool offset error. If the fingers close around the correct point and the cube slips during lift, inspect the contact shapes, friction, and gripper effort. Change one setting per reset.

## Self-check

The gripper reaches the nominated place pose, opens, and retreats. What evidence would make the episode a success?

<details>
<summary>Check your answer</summary>
<p>Check that the cube lifted clear of the support and that its measured pose and velocity satisfy a placement and settling criterion after release. The arm's pose only establishes that the arm reached its target.</p>
</details>

Use the plane-supported example as the manipulation baseline for the [tabletop capstone](/notes/capstone-tabletop/). For an elevated table, add a static collider and recompute the cube's spawn and goal heights relative to its top. Check reach from the arm's fixed base and include the table in the controller's obstacle model. Use the [bridge lab](/notes/isaac-ros-bridge/) to learn how an external program can interpret a simulated sensor stream.
