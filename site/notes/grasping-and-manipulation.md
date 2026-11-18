---
title: "Grasping and manipulation"
topic: "Planning and autonomy"
order: "052"
description: "Turn an object pose into a staged pick and place, then test how a grasp changes the planning scene."
prerequisites: "Coordinate frames, basic trigonometry, and search and motion planning."
minutes: 60
---

## Plan the grasp and what comes after it

A tabletop arm must move a block from a tray past a fixture. Closing the gripper at the right pose is one milestone. The approach must clear the tray, the fingers have to establish a stable grasp, and the retreat must carry the new combined shape past the fixture. A grasp that looks excellent in isolation can leave the arm with no feasible retreat.

Represent a grasp candidate as a tool pose relative to the object, plus a gripper opening and an approach direction. If `T_A_B` maps coordinates from B into A, compute `T_base_grasp = T_base_object × T_object_grasp` at the observation time. This convention also applies when the object was detected in a camera frame. A pregrasp is usually offset along the approach axis expressed in the grasp frame. For example, if the tool advances along its positive Z axis, moving 0.08 m back along that axis creates a pregrasp. Subtracting 0.08 m from base Z instead would give a different point for a tilted grasp. Include perception uncertainty when evaluating clearance at the rim and finger aperture. [Coordinate frames](/notes/coordinate-frames/) · [ROS 2 frames and time](/notes/ros2-frames-and-time/)

```text
Open fingers   Close and verify grip     Lift and transfer    Release
 pregrasp ---> grasp + block ----------> tool + block ------> place
                 |                            |                  |
Scene: block in world     attach block to tool link       detach to world
                              after grip evidence         after release
```

The upper line shows the motion stages and the lower line shows when collision geometry changes. Plan to the pregrasp, approach, close, verify the grip, attach the block in the scene, retreat, transfer, place, and confirm release. Stage transitions need observations. A simulated gripper can report jaw separation and contact. For a simple two-sided pinch with equal normal force `N` per finger and static friction coefficient `μ`, `2μN ≥ mg` is a necessary force balance for a symmetric static lift in the ideal friction model. Off-center loading adds torque, and acceleration or poor contact can cause slip. Gripper completion alone gives weak evidence of a secure hold. In a simulation, check separation and contact, then measure object motion relative to the tool after a small lift.

## Choose the space that expresses the constraint

The **task space** describes the tool pose. The **joint space** describes the joint values. Forward kinematics maps joints to the tool. Inverse kinematics (IK) can give several joint solutions for one target, such as elbow up and elbow down. Some targets are unreachable. Near a singular configuration, the Jacobian that maps joint rates to tool velocity loses rank or becomes poorly conditioned. A small Cartesian request in a difficult direction can require large joint changes. Seed successive IK solves from the previous solution when practical, and check joint limits and continuity. A straight line between two joint vectors can bend the tool path through a tray wall. Conversely, a straight Cartesian approach can fail before the final target even when that target has valid IK.

A common design uses free-space joint planning for transfer and Cartesian motion for a short constrained approach and retreat. Rank multiple grasp candidates by reachability, clearance, and whether the approach and lift can both be planned. A geometric path describes where the robot will go. A timed joint trajectory also describes when it should be there, within velocity and acceleration limits. Check the start against fresh measured joints, submit the timed trajectory, and observe tracking error and the action result before advancing. Cancel on a relevant fault and confirm the resulting controller and robot state before considering another plan. [ROS 2 actions](/notes/ros2-communication/) · [ros2_control Jazzy joint trajectory controller](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html)

## Update collision geometry when the grip changes

A planning scene combines robot state and geometry, obstacles, attached bodies, and collision policy. On confirmed grasp, transition one object from a world pose to a pose fixed relative to the appropriate tool link. Permit only the intended finger-object contacts. Check the attached geometry against obstacles and relevant robot links. On release, update its world pose from measured or simulated state. An attachment in the scene changes geometric collision queries. The real or simulated controller's payload dynamics and grip feedback have their own interfaces.

In MoveIt 2 on ROS 2 Jazzy, the C++ `PlanningSceneInterface` offers `applyAttachedCollisionObject` to apply an attachment synchronously to `move_group`. The header documents that separate scene monitors need to subscribe to the monitored scene to receive that update. Confirm the scene seen by the planner before using a transfer trajectory. `MoveGroupInterface::computeCartesianPath` returns a completion fraction. A partial prefix can be useful for diagnosing where an approach fails. Require a complete, validated approach for a stage whose goal is contact at the target. These details come from the Jazzy source. [Jazzy planning-scene interface](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning_interface/planning_scene_interface/include/moveit/planning_scene_interface/planning_scene_interface.hpp) · [Jazzy Cartesian path interface](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning_interface/move_group_interface/include/moveit/move_group_interface/move_group_interface.hpp)

## Lab: invalidate a transfer when the payload is attached

Save as `carry.py` and run `python carry.py`. On a two-dimensional slice of the tabletop, a two-link model has lengths 0.45 and 0.35 m. For target `(x, y)`, the law of cosines gives `cos(q2) = (x² + y² − L1² − L2²)/(2 L1 L2)`. Select the positive `q2` branch and compute `q1` by subtracting the second link's angular offset from the target bearing. The geometry check models the tool and a centered payload as disks. It computes the exact minimum clearance for each straight tool segment by projecting the fixture center onto that segment, clamping the projection to its endpoints, and subtracting both radii. The IK sampling demonstrates reach on one branch. Link collisions, joint limits, orientation, and timing would need their own checks in a full arm model.

```python
from math import acos, atan2, cos, hypot, sin

LINK_1, LINK_2 = 0.45, 0.35
START, GOAL = (0.35, 0.20), (0.75, 0.20)
FX, FY, FIXTURE_R = 0.55, 0.27, 0.03


def ik(x, y):
    cosine = (x*x + y*y - LINK_1**2 - LINK_2**2) / (2 * LINK_1 * LINK_2)
    q2 = acos(cosine)
    q1 = atan2(y, x) - atan2(LINK_2 * sin(q2), LINK_1 + LINK_2 * cos(q2))
    return q1, q2


def check(path, tool_radius):
    clearance = float("inf")
    for (x, y), (ex, ey) in zip(path, path[1:]):
        dx, dy = ex - x, ey - y
        length_sq = dx*dx + dy*dy
        t = ((FX - x) * dx + (FY - y) * dy) / length_sq if length_sq else 0
        t = min(1, max(0, t))
        gap = hypot(x + t*dx - FX, y + t*dy - FY) - FIXTURE_R - tool_radius
        clearance = min(clearance, gap)
        for step in range(21):
            px, py = x + dx*step/20, y + dy*step/20
            q1, q2 = ik(px, py)
            rx = LINK_1*cos(q1) + LINK_2*cos(q1 + q2)
            ry = LINK_1*sin(q1) + LINK_2*sin(q1 + q2)
            assert hypot(rx - px, ry - py) < 1e-9
    return clearance


straight = [START, GOAL]
detour = [START, (0.35, 0.12), (0.75, 0.12), GOAL]
for label, path, radius, feasible in [
    ("empty straight", straight, 0.015, True),
    ("loaded straight", straight, 0.050, False),
    ("loaded detour", detour, 0.050, True),
]:
    gap = check(path, radius)
    assert (gap > 0) == feasible
    print(f"{label}: minimum tool-fixture clearance {1000*gap:+.0f} mm")
```

Expect +25, −10, and +70 mm respectively. The centerline and IK samples for the two straight runs are identical. The geometry alone changes the verdict. In a simulator, save the scene snapshot, target poses, first rejected configuration, and collision pair. For runtime diagnosis, separate pose estimation error, planner rejection, controller tracking failure, and object slip by comparing timestamped tool, joint, and object observations. Report per-stage success, planning latency, minimum clearance, and final placement error. Test reachable and unreachable poses, stale observations, and a deliberately blocked retreat before any supervised commissioning. The tabletop capstone expands the work into an evidence-producing experiment. [Tabletop capstone](/notes/capstone-tabletop/)

## Exercises

1. A grasp candidate offsets the carried disk 0.02 m toward the fixture along base +Y, with the orientation fixed throughout the transfer. Predict and check the loaded straight clearance.

<details>
<summary>Solution</summary>

The carried centerline is now at `y = 0.22`. The gap is `0.27 − 0.22 − 0.03 − 0.05 = −0.03 m`. For this fixture, simulate the offset in the lab by moving the fixture down 0.02 m for the payload check while keeping IK unchanged. A rotating tool would require applying the attachment transform at each pose.

</details>

2. The transfer plans in simulation, but the block remains on the tray after the lift. The scene shows it attached. Which evidence should gate the transition, and how would you test it?

<details>
<summary>Solution</summary>

Treat attachment as a prediction about geometry once grip evidence passes. Require simulated contact and plausible finger separation, then verify the relative tool-to-object transform during a short validated lift. Inject a grasp with offset fingers that close without acquiring the block. Check that the executive aborts or reconciles the scene before authorizing transfer. Record gripper results and the object's actual state alongside the scene update.

</details>

## Summary

Plan the approach, grasp, retreat, and release as stages with observed completion conditions. Use task space to express tool constraints and joint space to check what the arm can do. Revalidate the scene and timed motion after the payload changes the robot's geometry.
