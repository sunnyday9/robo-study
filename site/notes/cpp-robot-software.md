---
title: "From Python to C++: build and test a robot software component"
topic: ROS 2
order: "065"
description: Port a pure wheel command calculation to C++, then attach it to a Jazzy node without moving a robot.
prerequisites: Basic Python, differential drive, a C++17 compiler; Jazzy only for the ROS extension.
minutes: 65
---

## Separate the algorithm from the graph

Your team has a wheel-rate calculation in Python. You need a C++ component because the robot's existing integration layer uses `rclcpp`. Rewriting the whole application is a bad first step: it changes numeric behavior, memory behavior, build system, and delivery at once. Port the pure calculation first, then let the ROS wrapper supply messages and inspect its output. Keep both versions on the same fixtures.

```text
  Python reference and handwritten checkpoints
      └─▶ compare with pure C++ function ──▶ compile and run locally
            └─▶ wrap in rclcpp ──▶ synthetic input ──▶ diagnostic output
```

For a differential drive, with wheel radius `r = 0.05 m` and track `b = 0.30 m`, compute `left = (v − bω/2)/r` and `right = (v + bω/2)/r`. A straight `0.20 m/s` command produces 4 rad/s on both wheels. At the same speed and `0.40 rad/s` yaw, the raw rates are 2.8 and 5.2. Scale both by the same factor to respect a 5 rad/s limit. Clipping them separately changes the desired curvature; jointly scaling slows speed and yaw together. This is a toy control contract, not a motor driver.

## Compile the pure function first

Download [wheel_command.cpp](/assets/labs/wheel_command.cpp) and save it next to your terminal. Run:

```bash
c++ -std=c++17 -Wall -Wextra -Werror wheel_command.cpp -o wheel_command
./wheel_command
```

The file uses a small value type for rates and `std::optional` to represent invalid input. That is clearer than returning a sentinel that could be mistaken for a valid motion request. It also checks the intermediate result against floating-point overflow. Its tests cover straight motion, curvature after limiting, and an input that is not a finite number. Build without `-DNDEBUG` so assertions execute. A larger project should use its test runner rather than put test assertions in a production executable.

Change both wheel calculations to use a plus sign for yaw. The straight run still passes, but the curved fixture fails. Restore it. That is why a useful port uses physically meaningful cases rather than sampling only “ordinary-looking” numbers.

## Wrap the calculation in ROS 2 Jazzy

This extension needs a sourced [Jazzy workspace](/notes/ros2-workspaces/), a C++ compiler, and an isolated simulation or local ROS domain. It subscribes to a synthetic input and only logs values; do not connect it to a controller. Use a dedicated workspace for this example so build or environment problems are easier to locate.

```bash
source /opt/ros/jazzy/setup.bash
mkdir -p ~/wheel_ws/src
cd ~/wheel_ws/src
ros2 pkg create wheel_diagnostics --build-type ament_cmake --license Apache-2.0 \
  --dependencies rclcpp geometry_msgs
```

In `wheel_diagnostics/src/wheel_diagnostics.cpp`, paste the declaration and function from the downloaded file, stopping before its first `int main()`. Append:

```cpp
#include <memory>
#include "geometry_msgs/msg/twist.hpp"
#include "rclcpp/rclcpp.hpp"

int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("wheel_diagnostics");
  auto subscription = node->create_subscription<geometry_msgs::msg::Twist>(
    "/study/wheel_probe", 10,
    [logger = node->get_logger()](geometry_msgs::msg::Twist::ConstSharedPtr message) {
      const auto wheel_rates = to_wheels(message->linear.x, message->angular.z);
      if (!wheel_rates) {
        RCLCPP_WARN(logger, "Invalid synthetic command");
        return;
      }
      RCLCPP_INFO(logger, "L=%.3f R=%.3f rad/s", wheel_rates->left, wheel_rates->right);
    });
  rclcpp::spin(node);
  subscription.reset();
  rclcpp::shutdown();
  return 0;
}
```

Add the following **before** the existing `ament_package()` in `wheel_diagnostics/CMakeLists.txt`. Keep the generated `find_package` lines for `rclcpp` and `geometry_msgs`; add one if it is missing.

```cmake
add_executable(wheel_diagnostics_node src/wheel_diagnostics.cpp)
target_compile_features(wheel_diagnostics_node PRIVATE cxx_std_17)
ament_target_dependencies(wheel_diagnostics_node rclcpp geometry_msgs)
install(TARGETS wheel_diagnostics_node DESTINATION lib/${PROJECT_NAME})
```

In each shell, use the [workspace chapter's local-discovery settings](/notes/ros2-workspaces/). Build in `~/wheel_ws` with `colcon build --packages-select wheel_diagnostics`, then source `~/wheel_ws/install/local_setup.bash` in the run shell and start the node with `ros2 run wheel_diagnostics wheel_diagnostics_node`. In a second isolated shell send a synthetic message:

```bash
ros2 topic pub --once /study/wheel_probe geometry_msgs/msg/Twist \
  '{linear: {x: 0.2}, angular: {z: 0.4}}'
```

Expected: `L=2.692 R=5.000 rad/s`. The subscription handle stays alive for the entire spin. Do not discard it when constructing a component: a built executable and visible node do not prove it has an active subscription. If the pure binary passes and the node prints nothing, check package discovery, topic name, type, endpoint QoS and the shell domain before editing the math.

## Exercises

Would independently clipping raw rates of 2.8 and 5.2 preserve the same ratio?

<details>
<summary>Check the command geometry</summary>
<p>No. The ratio becomes 2.8/5 instead of 2.8/5.2. A shared scale preserves both the sign and proportion for this kinematic model.</p>
</details>

The C++ binary reports the correct rates, but the ROS node becomes slow after adding live logs. Is the numeric function the first thing to optimize?

<details>
<summary>Choose the first measurement</summary>
<p>No. Measure callback execution and dispatch delay separately. Compare with logging disabled on the same inputs and keep timing-critical work separate from reporting.</p>
</details>

## What to keep

Keep the pure fixtures, the exact build command, and the source-to-install path. The stand-alone binary establishes numeric behavior. The synthetic ROS run tests graph integration. Neither qualifies deadlines on production hardware. See the [Jazzy C++ publisher/subscriber guide](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Cpp-Publisher-And-Subscriber.rst) and [real-time budgets](/notes/real-time-and-cpp/).
