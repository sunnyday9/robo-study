---
title: "构建并运行 ROS 2 工作空间"
topic: "ROS 2"
order: "061"
description: "构建 Jazzy Python 节点并跟踪 shell 如何找到已安装的包。"
prerequisites: "Ubuntu 24.04 上的基本 Python 和 Bash shell。"
minutes: 40
---

## 让队友的 shell 成为验收测试

你可以在编辑器中运行 Python 文件并查看其打印语句。你的队友需要从新的 shell 中通过包和可执行文件名称启动相同的组件，可能从也启动记录器的启动文件中启动。你们俩都需要知道运行的是哪个代码副本。这就是工作空间要解决的问题。在使用 ROS 2 Jazzy 的 Ubuntu 24.04 上，构建一个名为 `tabletop_tools` 的小软件包，找到其安装的前缀，然后启动 `heartbeat` 并在第二个终端中接收 `beat N`。这些是单独的检查点。将命令及其输出保存在第一个失败的命令处。

心跳可以让你在拥有机器人之前搭建好工作台。选择一个无需其他库即可看到其正确性的有效负载：格式化为文本的递增整数。选择一项要改变的设置：消息之间的间隔。在 0.5 秒的周期内，标称计划是每秒两条消息。侦听器可以中途加入，因此首先看到 `beat 7` 就可以了。心跳有助于测试安装、发现和交付。仿真器观察稍后将需要带有单位、帧和时间戳的实际模式。

## 从源头到流程全程跟踪

<figure class="lesson-figure">
  <a href="/assets/figures/ros-workspace.svg"><img src="/assets/figures/ros-workspace.svg" width="640" height="494" loading="lazy" decoding="async" alt="编辑源代码，构建并安装包，在运行 shell 中获取覆盖层，然后启动节点并从另一个 shell 观察心跳。"></a>
  <figcaption>每一步都证明了不同的事情。如果包已构建但心跳丢失，请验证每个 shell 正在使用哪个已安装的覆盖层和可执行文件。</figcaption>
</figure>

`/opt/ros/jazzy` 的 Jazzy 安装是底层。根据它构建你的工作空间。覆盖层是工作区的已安装输出，当你在底层之后获取它时，它提供的包优先。可以将其想象为一次将本地构建添加到多个搜索路径。 Python的导入路径只是其中之一。

```text
~/robo_ws/src/tabletop_tools/
    package.xml                 -> ROS package identity + dependencies
    resource/tabletop_tools     -> installed ament index marker
    setup.py + setup.cfg         -> install files + place executable wrapper
    tabletop_tools/heartbeat.py -> Python module with main()
                 |
           colcon build
                 v
~/robo_ws/install/tabletop_tools/
    share/ament_index/resource_index/packages/tabletop_tools
    lib/tabletop_tools/heartbeat
    ... installed Python module or symlink ...
                 |
           source local_setup.bash in run shell
                 v
ros2 run tabletop_tools heartbeat -> finds marker -> runs wrapper -> calls main()
```

阅读该图以区分打包证据和程序行为。该标记让 CLI 将包解析为安装前缀。 CLI 在 `lib/tabletop_tools` 下找到可执行文件后，生成的包装器将调用 Python 入口点。即使安装的工件丢失，该模块也可以导入。相反，如果包装器的依赖项或解释器错误，则包装器可能存在并在首次导入时崩溃。

`package.xml` 标识包并声明 rosdep 和 colcon 等工具的依赖关系。 `ament_python` 选择 Python 构建类型。脚手架的 `setup.py` 将包标记和清单注册为数据文件，并将 `heartbeat` 映射到 `console_scripts` 中的 `tabletop_tools.heartbeat:main`。 `setup.cfg` 将生成的可执行文件放在 `ros2 run` 查找的位置。对于普通的 Python 节点来说，这比 CMake 包的构建机制要少。当你稍后生成自定义 ROS 接口或构建本机代码时，请为该包使用适当的构建类型并声明使用包的依赖关系。本实验可以直接使用已安装的标准接口。

`colcon` 发现包并按依赖顺序构建它们。 `src/` 是你的可编辑输入，`build/` 具有中间产品，`log/` 可以帮助你调查构建失败。 `install/` 是正在运行的 shell 或另一个工作区使用的输出。本实验使用默认的独立布局，每个包都有一个前缀。 `install/setup.bash` 还链接构建时捕获的底层。我们在明确采购 Jazzy 后使用 `install/local_setup.bash`，因此 shell 的两层很容易重现。 [Jazzy工作区教程](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html)

## 实验室——发布合成心跳

按照 Jazzy Desktop 安装和开发工具步骤进行操作。使用新的 Ubuntu Bash shell，并停用任何 ML 虚拟环境，来获取包的底层和支架。该发行版的 ROS Python 扩展是为其系统解释器构建的。如果稍后添加 Python 环境，请在假设两个 shell 等效之前检查解释器和实际的 `import rclpy`。 [Jazzy Ubuntu 官方安装](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) · [Jazzy Python 软件包指南](https://github.com/ros2/ros2_documentation/blob/jazzy/source/How-To-Guides/Using-Python-Packages.rst)

```bash
source /opt/ros/jazzy/setup.bash
echo "$ROS_DISTRO"  # Expected: jazzy
mkdir -p ~/robo_ws/src
cd ~/robo_ws/src
ros2 pkg create --build-type ament_python --license Apache-2.0 \
  --node-name heartbeat tabletop_tools --dependencies rclpy rcl_interfaces std_msgs
```

将 `~/robo_ws/src/tabletop_tools/tabletop_tools/heartbeat.py` 替换为该可运行节点。保留生成的打包文件。参数使间隔成为测试输入，无需源编辑。在启动时读取并验证一次，然后创建计时器。回调拥有序列并在每次发布后递增它。 `spin` 使进程可用于运行准备好的工作，并且清理可以轻松停止、改变一个输入并重新启动。

```python
"""Publish a synthetic sequence for the tabletop labs."""

import math

from rcl_interfaces.msg import ParameterDescriptor
import rclpy
from rclpy.executors import ExternalShutdownException
from std_msgs.msg import String


def main():
    """Run the heartbeat until the ROS context shuts down."""
    rclpy.init()
    node = rclpy.create_node('tabletop_heartbeat')
    try:
        period = node.declare_parameter(
            'period_s', 0.5, ParameterDescriptor(read_only=True)
        ).value
        if not math.isfinite(period) or period <= 0.0:
            raise ValueError('period_s must be finite and positive')

        publisher = node.create_publisher(String, '/tabletop/heartbeat', 10)
        sequence = 0

        def tick():
            nonlocal sequence
            publisher.publish(String(data=f'beat {sequence}'))
            sequence += 1

        node.create_timer(period, tick)
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
```

从仅底层 shell 中的工作区根目录进行构建。如果从未在本机上配置过 rosdep (`sudo rosdep init`)，则初始化一次 rosdep。 `rosdep` 将依赖项密钥解析为主机的程序包。即使你自己的构建已经成功，它也可以帮助队友重现你已安装的内容。 `--packages-select` 在这里就足够了，因为依赖项来自 Jazzy。如果你将源依赖项添加到此工作区，`--packages-up-to tabletop_tools` 可以构建所选包及其工作区依赖项。

```bash
cd ~/robo_ws
colcon list
rosdep update
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon build --symlink-install --packages-select tabletop_tools
```

将以下内容另存为 `~/robo_ws/lab-env.bash`。使用 `source ~/robo_ws/lab-env.bash` 在每次新运行或观察者终端中获取它。保留一个单独的构建外壳，仅包含 Jazzy 底层。如果域 72 被占用，请在帮助程序中选择不同的未使用域并一致地使用它。该实验室使用 Jazzy Fast DDS 并将发现保持在一台机器本地。

```bash
source /opt/ros/jazzy/setup.bash || return 1
source "$HOME/robo_ws/install/local_setup.bash" || return 1
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DOMAIN_ID=72 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
unset ROS_STATIC_PEERS ROS_LOCALHOST_ONLY
```

Sourcing 将环境更改应用于当前 shell。以 `bash lab-env.bash` 身份运行帮助程序会将它们应用到退出的子进程中。将设置保留在特定于项目的帮助程序中可以使两个终端的比较可重复，而无需更改计算机上的每个 Bash 会话。留在底层上的构建外壳还可以避免意外使用同一覆盖层的早期构建中的工件。 [Jazzy 发现设置](https://docs.ros.org/en/jazzy/Tutorials/Advanced/Improved-Dynamic-Discovery.html)

在终端 A 中，找到并运行可执行文件。预期的前缀是 `$HOME/robo_ws/install/tabletop_tools`，预期的可执行文件列表是 `tabletop_tools heartbeat`。

```bash
ros2 pkg prefix tabletop_tools
ros2 pkg executables tabletop_tools
ros2 run tabletop_tools heartbeat
```

在终端 B 中，使用 `timeout 5s ros2 topic echo /tabletop/heartbeat --once`。预期响应为 `data: beat N`。然后运行 ​​`ros2 topic hz /tabletop/heartbeat` 几秒钟并使用 Ctrl+C 停止速率观察器。其报告的速率估计了达到该订阅的内容。发现、调度和观察者负载都会影响它。

## 改变间隔并预测移动

保持工作空间、外壳和观察者固定。使用 Ctrl+C 停止 A，然后使用 `ros2 run tabletop_tools heartbeat --ros-args -p period_s:=0.25` 重新启动。在 B 中，确认 `ros2 param get /tabletop_heartbeat period_s`，然后重复速率探测。预计参数读数为 0.25，接收速率从大约 2 Hz 上升到 4 Hz。这些是根据配置的时间段进行的预测。写下你的实际利率和观察窗口。当进程重新启动时，预计计数器会重置。

如果实时参数正确但汇率几乎没有变化，请使用 `ros2 topic info -v /tabletop/heartbeat` 检查哪个发布者处于活动状态。不止一家出版商破坏了这种比较。如果存在并且交付不一致，请在更改计时器代码之前检查计时和资源负载。尝试在运行时设置 `period_s` 并期待拒绝：该节点在启动时调整计时器大小并声明参数为只读。支持实时更新需要显式验证和计时器更新路径。

## 诊断第一个故障层

| 第一个失败的探头 | 接下来要检查什么 |
| --- | --- |
| `colcon list` 省略封装 | 检查 `src/` 下的目录、清单和任何忽略标记。 |
| `ros2 pkg prefix tabletop_tools` 失败或返回错误的工作空间 | 比较新的底层加覆盖层外壳的结果。检查 `AMENT_PREFIX_PATH` 和来源订单。 |
| 前缀是正确的，但 `ros2 pkg executables tabletop_tools` 省略了 `heartbeat` | 检查 `console_scripts` 和 `setup.cfg` 中配置的脚本位置。重建包装变化。 |
| 包装器启动并引发回溯 | 跟踪失败的导入、启动输入或回调。从源树外部使用 `python3 -c 'import tabletop_tools.heartbeat as h; print(h.__file__)'` 确认模块路径。 |
| 进程保持运行但回显超时 | 比较 shell 并检查 [ROS 2 通信](/zh/notes/ros2-communication/) 中的发现和端点。 |

对于下一次迭代，临时编辑有效负载前缀，重新启动节点，并使用 echo 检查更改是否已进入流程。使用 `--symlink-install`，可以在重新启动时拾取对已链接的 Python 模块的更改，而无需构建。对入口点、依赖项或新安装的文件的更改仍然需要重建。复制安装需要额外的源代码编辑构建成本，并且在你想要测试固定工件时非常有用。恢复 `beat N` 有效负载并停止节点，然后再继续。

## 练习

1. 诊断不同的外壳。在新的终端中，仅使用 Jazzy。从包含 `setup.py` 的包目录中，尝试导入 `tabletop_tools.heartbeat`。然后尝试 `ros2 pkg prefix tabletop_tools`。在寻找助手之前预测结果。

<details>
<summary>解决方案</summary>
<p>有了可用的系统 ROS 依赖项，Python 就可以从其工作目录导入。 CLI 仍然需要在 ament 搜索路径上安装标记。获取帮助程序，更改到另一个目录，并验证前缀和可执行文件。这些检查确定安装是可见的，而不依赖于工作目录。</p>
</details>

2. 将工作流程转移到新的可执行文件。你可以在现有 Python 包中添加带有 `main()` 的 `diagnose.py`。你可以导入它，但要运行 `ros2 run tabletop_tools diagnose`。发生了什么变化，最小的验收测试是什么？

<details>
<summary>解决方案</summary>
<p>添加<code>诊断 = tabletop_tools.diagnose:main</code>到现有的控制台脚本。从仅底层 shell 重建包，在新运行的 shell 中获取覆盖层，并检查可执行列表是否包含<code>诊断</code>在开始之前。保留心跳条目。要独立于 DDS 检查启动行为，请为新命令提供一个小的可观察输出并从源目录外部运行它。</p>
</details>

## 常见的误解

- 每个终端都会继承我最新的构建环境。 shell 在启动时从其父级继承环境。在每个实验室 shell 中获取预期的覆盖和发现设置。
- 成功的构建证明该节点可以正常工作。它表明构建已完成。前缀查找、导入、进程启动和消息接收各自行使另一个边界。
- 0.25 秒定时器保证用户处的频率为 4 Hz。定时器提供标称周期。测量观察者的交付情况并根据该测量结果调查偏差。

## 总结

针对已知的底层进行构建，从新的覆盖 shell 中找到已安装的工件，然后从另一个进程测试可见行为。第一个失败的探测告诉你要调查哪个边界。一旦基线起作用，改变单个启动输入并使用相同的观察者测量结果。

- [Jazzy Python 包脚手架和入口点](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html)
- [Jazzy参数描述符定义](https://raw.githubusercontent.com/ros2/rcl_interfaces/jazzy/rcl_interfaces/msg/ParameterDescriptor.msg)
