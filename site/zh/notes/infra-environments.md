---
title: "搭建可复现的机器人开发环境"
topic: "Infrastructure"
order: "100"
description: "将 ROS 2、Isaac Sim 和 LeRobot 与主机匹配，并记录每个主机实际使用的版本。"
prerequisites: "熟悉 Python 和基本的 shell 命令"
minutes: 45
---

## 根据工作负载选择

你继承了一个在其作者的终端上运行的机器人演示。在你的笔记本电脑上导入策略，仿真器在另一台计算机上打开，ROS 订阅者将永远等待。你应该首先复制哪一部分？在两台机器上安装每个依赖项会使每个错误更难以隔离。确定每个进程欠下一个进程的输出，然后构建可以显示切换中断位置的最小测试。

你的目标是一个主机清单，队友可以使用它来重复三个范围检查。 Jazzy shell 导入其二进制客户端，并在本地 ROS 实验室中接收一条已知消息。 Isaac Sim 6.1.0 进程加载一个阶段，对其进行步进，并在合格的主机上生成预期状态或渲染帧。 Python 3.12 上的 LeRobot v0.4.3 环境会解码一个固定数据集样本，或者在运行仿真器练习时重置并执行 PushT。记录每个被阻止的检查的第一个缺失的先决条件。这为今天使用 CPU 笔记本电脑的开发人员提供了有用的工作，并为明天提供了对 GPU 插槽的具体请求。

| 主持人 | ROS 2 爵士乐 | Isaac Sim 6.1.0 | LeRobot v0.4.3 |
| --- | --- | --- | --- |
| 本机 Ubuntu 24.04 | 使用 Jazzy apt 包和系统 Python。本地重放或同主机桥的实用首选。分别检查硬件的设备权限和驱动程序。 | 用于场景编辑的工作站，用于可重复无头运行的 Linux 容器。两者都取决于支持的图形硬件和驱动程序。 | 使用专用的Python 3.12环境。解决该平台的 PyTorch 构建和视频后端问题。 |
| Windows 11 本机 | NVIDIA 通过 Pixi 为 Windows Isaac 桥提供原生 Jazzy 文档。如果桥接集成是任务，请遵循特定于版本的路线。 | 合格 RTX GPU 上的工作站应用程序。 GUI 可帮助你检查场景几何形状、接触和控制器行为。 | 标记元数据在 Windows 上省略 TorchCodec。使用真实示例确认 PyAV 解码路径和你的策略轮子。 |
| WSL2 中的 Ubuntu 24.04 | 适用于相同环境的 ROS 练习和本地包。 Windows 到 WSL 的流量跨越网络边界。 NVIDIA 将其 Windows 到 WSL 桥接设置标记为已弃用。 | WSL2 中成功的 CUDA 探测可检查计算可见性。本课程使用已记录的 Isaac 工作站或 Linux 容器主机。 | 从离线数据集或 PushT 开始。当工作负载需要时，将串行和相机直通视为单独的测试。 |
| 远程本机 Ubuntu 24.04 | 在工作负载旁边运行最小的本地重放并导出结果。 | 使用符合条件的 RTX 主机进行无头作业。为首次启动时使用空缓存配置资产并预留时间。 | 在策略允许的 CPU 上运行或安排单独的计算 GPU 作业。记录数据和输出的位置。 |

平台和版本参考。 [Jazzy Ubuntu 软件包](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/Ubuntu-Install-Debs.rst)、[Isaac Sim 6.1.0 要求](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/requirements.html)、[Isaac Sim ROS 2 安装](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_ros.html)、[LeRobot v0.4.3 安装](https://huggingface.co/docs/lerobot/v0.4.3/en/installation)、[LeRobot v0.4.3 包元数据](https://github.com/huggingface/lerobot/blob/v0.4.3/pyproject.toml)。

从最困难的约束开始。如果交付的是 Isaac 相机框架，则可以训练小型 PyTorch 模型的主机可能仍然缺乏所需的图形功能。 NVIDIA 的 6.1.0 x86-64 表在其最小列中列出了 RTX 4080 和 16 GB VRAM。作为下限计算，四台 1920 × 1080 相机（带有 1 个 RGBA8 和 1 个 float32 深度缓冲区）的一组输出缓冲区各占用约 66 MB。仿真器还需要 VRAM 用于纹理、阶段数据和中间渲染缓冲区。仅凭缓冲区大小无法预测总使用量。在增加场景或传感器负载之前测试单个相机。如果可交付成果是数据集转换，则运行具有代表性解码的 CPU 可以回答眼前的问题。 [Isaac Sim 6.1.0 要求](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/requirements.html)。

## 保持 Python 运行时明确

Jazzy `.deb` 软件包附带本机库和编译的 Python 扩展。导入 `rclpy` 需要 Python 查找包、加载为解释器的应用程序二进制接口 (ABI) 构建的扩展，并解析其共享库。这是三项不同的检查。使用 Ubuntu 的系统解释器。获取 `/opt/ros/jazzy/setup.bash` 以公开 apt 安装。如果在本地开发 ROS 包，请针对该底层构建工作区，然后在运行 shell 中获取工作区覆盖层。然后可以看到包的两个版本，因此请检查 `rclpy.__file__` 和 `ros2 pkg prefix <package>` 以查看已解决的问题。 [ROS 2 Python 兼容性指南](https://github.com/ros2/ros2_documentation/blob/jazzy/source/How-To-Guides/Using-Python-Packages.rst)。

对 LeRobot 使用新的终端和单独的 Python 3.12 环境。 v0.4.3 包接受 Python 3.10 及更高版本。如果设置 ML 环境，请为 PushT 实验室指定 `lerobot[pusht]==0.4.3`，选择你的 CPU 或 CUDA 轮源，并解析特定于平台的锁（包括传递依赖项）。保留锁及其生成命令。通过包含哈希值的 pip 兼容锁，可以使用 `python -m pip install --require-hashes -r requirements-linux-x86_64.lock` 安装干净的环境。该文件名描述了你提供的输入，即使在同一架构上，Linux CPU 和 CUDA 也可能需要不同的锁。如果两个环境必须使用相同的发行版，请保留轮哈希和索引来源。最后运行示例解码。默认解码器选择会检查是否可以找到 TorchCodec，因此发现的包仍可能无法加载本机依赖项。 [标记 LeRobot 要求](https://github.com/huggingface/lerobot/blob/v0.4.3/pyproject.toml)，[标记解码器实现](https://github.com/huggingface/lerobot/blob/v0.4.3/src/lerobot/datasets/video_utils.py)，[pip 哈希检查](https://pip.pypa.io/en/stable/topics/secure-installs/)。

使用 Isaac 的特定版本启动器或 Python 环境来执行仿真器脚本。这是桥接模拟和单独的策略实验室的流程边界。

```text
Isaac launcher -> Franka stage -> bridge publishes /clock and state
                                          |
                                          v
                             Jazzy Python -> receives -> bag
                                                          |
                                                          v
                                           optional, explicit adapter
                                           (schema, units, timing)

Python 3.12 venv -> LeRobot v0.4.3 -> pinned data and PushT lab
```

箭头显示在哪里测试合约。仅当两个时间相当、都属于同一事件并且记录器记录关联时，标记为 100 ms 的说明性观察和标记为 107 ms 的命令才形成可用对。 7 毫秒的偏差适合 10 毫秒的预算。在行动之前指定观察并使用一个仿真时钟。在 Isaac 可以向 LeRobot 提供数据之前，适配器必须映射字段、功能顺序、单位和操作。 PushT 实验室使用自己的数据集和环境。支持的进程内集成可以避免序列化开销。单独的进程可能会产生副本并需要接口测试，但可以让你独立地解决依赖关系并重现故障。

## 实验室·盘点一台主机

**设计并运行。**为每个工作负载提供命令、预期可观察值和状态。从 ROS 导入开始，不需要仿真器。在预配置的 Ubuntu 或 Ubuntu WSL2 主机上，在新的 ROS shell 中运行这些 Bash 命令。如果安装文件丢失，请停止 ROS 探针并记录该先决条件。

```bash
cat /etc/os-release
uname -m
uname -r
source /opt/ros/jazzy/setup.bash
printf 'ROS distro=%s\n' "$ROS_DISTRO"
dpkg-query -W ros-jazzy-rclpy
/usr/bin/python3 -c "import sys, rclpy; print(sys.executable, rclpy.__file__)"
/usr/bin/python3 -c "from rclpy.utilities import get_rmw_implementation_identifier; print(get_rmw_implementation_identifier())"
```

**Observe.**预期的导入行以 `/usr/bin/python3` 开头，并指向干净的 apt 设置上的 Jazzy 安装。在单独的、已激活的 LeRobot shell 中，运行 `python --version`、`python -m pip show lerobot torch` 和以下探测器。即使版本字符串与 ROS 解释器匹配，也要使用报告中的解释器路径。

```bash
python -m pip check
python -c 'import sys, torch; print(sys.executable, torch.__version__, torch.version.cuda, torch.cuda.is_available())'
```

`pip check` 检查声明的包关系。 CPU 版本可能会在最后两个字段中显示 `None False`，这对于仅 CPU 的目标来说是可以接受的。在 Windows 上，PowerShell 中的 `wsl --list --verbose` 区分 WSL1 和 WSL2。记录来自 NVIDIA 主机上的应用程序或图像元数据的仿真器构建以及来自 `nvidia-smi` 的 GPU 和驱动程序。

**变化并解释。**成功导入ROS后，用`env -u PYTHONPATH /usr/bin/python3 -c "import sys, rclpy; print(sys.executable, rclpy.__file__)"`重复它。这会更改一个命令的一个变量。一个说明性的结果是 `ModuleNotFoundError: No module named 'rclpy'`。如果仍然导入，请检查其他安装的路径或配置的搜索路径。已找到包但由于缺少共享对象而失败，需要进行库路径调查。通过重新运行原始命令来恢复基线，然后从导入前进到网络章节中的本地综合主题测试。

**Checkpoint.**保存操作系统版本、内核、架构、本机与 WSL2、GPU 和驱动程序、ROS 包版本和中间件实现、仿真器构建、Python 可执行路径、ML 锁定修订和数据集修订。在通过、失败或跳过的旁边附上实际观测结果。从另一个 shell 继承的过时的 `ROS_DISTRO` 可能会误导你。记录导入模块的路径。当另一个人可以知道要打开哪个环境以及期望哪个结果时，清单就完成了。

## 练习

<details>
<summary>调试 · 两个 shell 都使用 Python 3.12，但 ML shell 无法导入 rclpy。哪个测试先进行？</summary>
<p>在干净的、有来源的 ROS shell 中使用系统解释器重复导入。如果通过，则将可执行文件、包路径和本机库解析与失败的进程进行比较。保持 ML shell 独立并安排消息或文件移交。如果干净检查也失败，请在调查 ML 锁之前检查软件包安装和环境。</p>
</details>

<details>
<summary>转移 · 计划一个下午的时间，使用 CPU 笔记本电脑和两个小时的远程 RTX 插槽</summary>
<p>运行本地 Jazzy 导入和消息检查，并解码笔记本电脑上固定的 LeRobot 示例。在保留之前准备好固定阶段、预期输出和可写结果目录。在远程主机上，清点驱动程序，启动特定于版本的兼容性检查，并使用日志运行一项有界 Franka 试验。利用剩余时间更改一个场景或传感器设置。使用自己的数据集和环境记录本地 PushT 实验。</p>
</details>

## 常见的误解

- **“两个环境都报告 Python 3.12，因此我可以将它们组合起来。”**包解析、扩展 ABI 和共享库解析都需要证据。
- **“我的 shell 可以看到 CUDA，因此相机可以工作。”**检查图形堆栈、场景加载、传感器配置和渲染节奏。
- **“我的安装说明中的版本标识了运行。”**记录安装程序解决的工件、使用的启动程序以及实际主机。

## 总结

从工作负载必须产生的输出中选择一个主机。在小测试中证明每个解释器、导入和硬件相关的功能。记录已解决的版本和一项已知的观测结果，然后改变你可以恢复的输入。当你跨越流程边界时，请显式测试格式和时钟约定。

将清单带到 [桌面顶点](/zh/notes/capstone-tabletop/) 并将相关的运行时详细信息附加到每个阶段。接下来，[打包 GPU 工作负载](/zh/notes/infra-containers-gpu/)。
