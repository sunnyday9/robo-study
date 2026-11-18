---
title: "从 Python 到 C++：构建并验证机器人软件组件"
topic: "ROS 2"
order: "065"
description: "将纯轮命令计算移植到 C++，然后将其附加到 Jazzy 节点，而无需移动机器人。"
prerequisites: "基础Python、差分驱动、C++17编译器； Jazzy 仅适用于 ROS 扩展。"
minutes: 65
---

## 将算法与图分开

你的团队使用 Python 进行轮速计算。你需要 C++ 组件，因为机器人的现有集成层使用 `rclcpp`。重写整个应用程序是一个糟糕的第一步：它会立即改变数字行为、内存行为、构建系统和交付。首先移植纯计算，然后让 ROS 包装器提供消息并检查其输出。将两个版本保留在相同的装置上。

```text
  Python reference and handwritten checkpoints
      └─▶ compare with pure C++ function ──▶ compile and run locally
            └─▶ wrap in rclcpp ──▶ synthetic input ──▶ diagnostic output
```

对于差速驱动器，车轮半径为 `r = 0.05 m`，轮距为 `b = 0.30 m`，计算 `left = (v − bω/2)/r` 和 `right = (v + bω/2)/r`。直接的 `0.20 m/s` 命令会在两个车轮上产生 4 rad/s。在相同速度和 `0.40 rad/s` 偏航下，原始速率分别为 2.8 和 5.2。将两者缩放相同的系数以遵守 5 rad/s 限制。分别修剪它们会改变所需的曲率；联合缩放会同时减慢速度和偏航。这是玩具控制合约，而不是电机驱动程序。

## 首先编译纯函数

下载 [wheel_command.cpp](/assets/labs/wheel_command.cpp) 并将其保存到你的终端旁边。运行：

```bash
c++ -std=c++17 -Wall -Wextra -Werror wheel_command.cpp -o wheel_command
./wheel_command
```

该文件使用小值类型的费率和 `std::optional` 来表示无效输入。这比返回可能被误认为有效动议请求的哨兵更清楚。它还检查中间结果是否存在浮点溢出。其测试涵盖直线运动、限制后的曲率以及非有限数的输入。不使用 `-DNDEBUG` 进行构建，以便执行断言。较大的项目应该使用其测试运行程序，而不是将测试断言放入生产可执行文件中。

更改两个车轮计算以使用加号表示偏航。直线仍然可以通过，但是弯曲的夹具失败。恢复它。这就是为什么有用的端口使用物理上有意义的案例，而不是仅对“看起来普通”的数字进行采样。

## 将计算包装在 ROS 2 Jazzy 中

此扩展需要一个来源的 [Jazzy 工作区](/zh/notes/ros2-workspaces/)、一个 C++ 编译器以及一个隔离的模拟或本地 ROS 域。它订阅合成输入并仅记录值；不要将其连接到控制器。本示例使用专用工作区，以便更容易找到构建或环境问题。

```bash
source /opt/ros/jazzy/setup.bash
mkdir -p ~/wheel_ws/src
cd ~/wheel_ws/src
ros2 pkg create wheel_diagnostics --build-type ament_cmake --license Apache-2.0 \
  --dependencies rclcpp geometry_msgs
```

在 `wheel_diagnostics/src/wheel_diagnostics.cpp` 中，粘贴下载文件中的声明和函数，在第一个 `int main()` 之前停止。附加：

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

在 `wheel_diagnostics/CMakeLists.txt` 中现有的 `ament_package()` 之前添加以下内容。保留 `rclcpp` 和 `geometry_msgs` 生成的 `find_package` 行；如果缺少则添加一项。

```cmake
add_executable(wheel_diagnostics_node src/wheel_diagnostics.cpp)
target_compile_features(wheel_diagnostics_node PRIVATE cxx_std_17)
ament_target_dependencies(wheel_diagnostics_node rclcpp geometry_msgs)
install(TARGETS wheel_diagnostics_node DESTINATION lib/${PROJECT_NAME})
```

在每个 shell 中，使用 [工作区章节的本地发现设置](/zh/notes/ros2-workspaces/)。使用 `colcon build --packages-select wheel_diagnostics` 构建 `~/wheel_ws`，然后在运行 shell 中获取 `~/wheel_ws/install/local_setup.bash` 并使用 `ros2 run wheel_diagnostics wheel_diagnostics_node` 启动节点。在第二个隔离 shell 中发送一条合成消息：

```bash
ros2 topic pub --once /study/wheel_probe geometry_msgs/msg/Twist \
  '{linear: {x: 0.2}, angular: {z: 0.4}}'
```

预期：`L=2.692 R=5.000 rad/s`。订阅句柄在整个旋转过程中保持活动状态。构建组件时不要丢弃它：构建的可执行文件和可见节点并不能证明它具有活动订阅。如果纯二进制文件通过并且节点不打印任何内容，请在编辑数学之前检查包发现、主题名称、类型、端点 QoS 和 shell 域。

## 练习

独立削减 2.8 和 5.2 的原始利率是否会保持相同的比率？

<details>
<summary>检查命令几何形状</summary>
<p>不会。比率变为 2.8/5，而不是 2.8/5.2。共享比例保留了该运动学模型的符号和比例。</p>
</details>

C++ 二进制文件报告了正确的速率，但添加实时日志后 ROS 节点变得很慢。数值函数是首先要优化的吗？

<details>
<summary>选择第一个测量值</summary>
<p>否。分别测量回调执行和调度延迟。与在相同输入上禁用的日志记录进行比较，并将时间关键型工作与报告分开。</p>
</details>

## 保留什么

保留纯粹的装置、准确的构建命令和源安装路径。独立的二进制文件建立数字行为。合成 ROS 运行测试图集成。两者都不符合生产硬件的最后期限。请参阅[Jazzy C++ 发布者/订阅者指南](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Cpp-Publisher-And-Subscriber.rst) 和[实时预算](/zh/notes/real-time-and-cpp/)。
