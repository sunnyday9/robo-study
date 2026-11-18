# Course review

The course assumes Python, data structures, and basic machine learning. It adds the robotics-specific contracts: coordinate frames, units, message time, bounded feedback, environment compatibility, and evaluation under closed-loop dynamics.

## Lecture edition

The [AI Systems Performance Engineering chapter materials](https://se7en.mintlify.app/books/ai-systems-performance-engineering/chapters/ch01) served as a teaching-format reference: explanatory sections, figures that support the argument, and optional details without interrupting the main path. This course uses original robotics examples. Each lecture starts with an engineering problem, explains a concrete mechanism, then asks the learner to build a small baseline, vary one input, and explain the result. Chapter outlines and collapsible solutions support longer sessions without putting answers in the reading path.

Review scope: keep the same 22 chapter routes, separate setup success from tool integration, and carry a single tabletop scenario across the course without implying that Isaac Sim recordings can be loaded into LeRobot as-is. Use runnable snippets where the prerequisites exist; distinguish source verification, measured toy results, and expected robotics runtime outcomes.

The lecture build rendered all 24 pages with unique IDs, valid internal links, and at least two exercise solutions per chapter. Browser verification covered outline navigation and revealing a solution. The coordinate, projection, feedback, and frame-selection snippets ran locally, and the trace validator accepted the baseline and rejected the tightened skew budget. The CPU capstone measured 0/3 time-only successes despite a low offline action error on the held-out fixture, versus 3/3 with feedback. This edition did not qualify the live ROS, Isaac Sim, or full LeRobot training and evaluation paths.

## Review decisions

| Area | What was reconciled |
| --- | --- |
| Environment | Ubuntu 24.04 and ROS 2 Jazzy are the ROS lab baseline. Isaac Sim 6.1.0 and LeRobot v0.4.3 are explicit teaching releases, not a claimed latest or jointly qualified stack. ROS, Isaac Sim, and LeRobot use separate runtimes. |
| Time and replay | The heartbeat exercise proves delivery, not timestamped geometry. The capstone adds a synthetic TF and stamped-pose bag fixture, with one replay clock and a checker that uses header stamps. |
| Simulation and learning | The packaged Franka example supplies the Isaac Sim baseline. PushT supplies an independent LeRobot evaluation path. Isaac-to-LeRobot export requires a supported integration or a checked adapter; none is bundled. |
| Evaluation | Keep episode groups intact, fit normalization only on training data for held-out tests, and report offline action error separately from closed-loop task success. |
| Infrastructure | The examples distinguish local discovery from network security, GPU visibility from rendering, and CPU checks from GPU qualification. |

Technical references are cited next to the steps they support, including [ROS bag playback source](https://raw.githubusercontent.com/ros2/rosbag2/jazzy/ros2bag/ros2bag/verb/play.py), [Isaac Sim 6.1.0 bridge setup](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_ros.html), and [LeRobot v0.4.3 training source](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/scripts/lerobot_train.py).

## Verification boundary

- Built the static course at the root and under the GitHub Pages project prefix; checked the 22-chapter index, sequence, exercise disclosures, assets, and local links.
- Verified that all three browser lab inputs update their outputs. Ran the Python trace validator against a passing fixture and a failing skew budget.
- Checked the robotics command examples against versioned upstream documentation or source and parsed the downloadable scripts. The LeRobot author ran the published PushT shard audit (206 episodes and 25,650 rows) and wrote and reopened two simulated episodes (40 frames). The ACT CLI accepted its arguments and began downloading data, but no checkpoint was produced.
- ROS integration, Isaac Sim/RTX, ACT training to completion, and closed-loop policy evaluation were not verified. Treat their expected results as learner checkpoints, not measured results.
- The site has no production npm dependencies. Full npm audit flagged the build-time `picomatch` chain; the current installed version was the latest published when checked. The static output does not include that dependency. Keep the generator and preview server on trusted local or CI inputs, and recheck before upgrading.
