---
title: "搭建并验证 Isaac Sim 环境"
topic: "Isaac Sim"
order: "081"
description: "固定受支持的仿真器、驱动程序和 ROS 2 组合，然后隔离启动、渲染和资产故障。"
prerequisites: "舒适地运行 Python 和 shell 命令"
minutes: 35
---

## 工作环境证明了什么

想象一下借用一台 GPU 机器来收集腕式相机演示。你的训练脚本会看到 CUDA 并且仿真器打开，但机器人引用为空，并且相机流永远不会到达。堆栈中实际已经传递了多少内容？如果你在安装所有内容之前回答该问题，则可以诊断第一个失败的边界，而不是一起更改驱动程序、Python 环境和 ROS 设置。

建立一台机器的验收记录。第一个有用的结果是一个可见的刚性立方体掉落并停在平面上，然后在单独的无头 Python 进程中成功更新。这些观察涵盖了不同的执行路径。后面的章节通过引用的 Franka 资产、功能控制器和标记的 ROS 相机流扩展了记录。在你花时间设计完整的实验之前，检查点会揭示机器可以支持的功能。

该轨道在 x86-64 上使用 Isaac Sim 6.1.0 独立二进制文件。完整轨道的参考路径是使用标准接口的本机 Ubuntu 24.04 和 ROS 2 Jazzy。 Windows 11 可以运行工作站版本。它的桥有一个单独的特定于平台的设置，因此如果你想逐字遵循 ROS 实验室，请使用 Linux 参考路径。 NVIDIA 支持 Linux 上的 Isaac Sim 容器。在 Mac 或不支持 RTX GPU 的计算机上，使用支持的远程模拟主机或在本地完成 capstone 的回放阶段。 [NVIDIA要求](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/requirements.html) · [ROS 2平台矩阵](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_ros.html)

| 决定 | 安装前要验证什么 |
| --- | --- |
| 仿真器 | 将下载、文档、示例和资产与同一版本相匹配。安装的 `VERSION` 文件标识了版本。 |
| 主机及驱动 | 将操作系统、GPU、VRAM、RAM 和存储与版本矩阵进行比较。 NVIDIA 将具有 16 GB VRAM 的 RTX 4080 列为 x86-64 最低规格，并记录了其测试的驱动程序。检查驱动程序说明以了解你的具体 GPU。 |
| ROS 2 | 一起检查主机操作系统、ROS 发行版和中间件。仅在基础模拟工作后添加桥。 |
| 执行方式 | 使用桌面视口检查场景。使用独立的 Python 进行具有固定停止条件的脚本运行。 Headless 移除了窗口，但仍然可以在 GPU 上渲染相机。 |

## 遵循组件边界

```text
Host OS and driver
  |  GPU enumeration is the first probe (nvidia-smi)
  v
Kit process and enabled extensions
  |-- USD composition loads scene descriptions and asset references
  |-- PhysX reads physics schemas and advances rigid-body state
  |-- RTX renderer turns scene state into pixels and sensor products
  `-- ROS 2 bridge serializes selected state or sensor data
        |
        v
      Separate Jazzy process receives messages over middleware
```

将其视为依赖关系图。资产解析、物理和渲染是运行的应用程序内的不同功能。用内置形状制作的立方体可以在零机器人下载的情况下运行解算器和视口。如果该调查通过并且所参考的机器人丢失，调查将转向资产构成。视口中的一张图片验证一个渲染路径。桥订阅者仍然需要配置的渲染产品、启用的发布者和兼容的中间件设置。使用距离故障最近的探测器来决定接下来要查找的位置。 [NVIDIA参考架构](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/introduction/reference_architecture.html)

工作站启动器启动一个 Kit 应用程序来管理自己的更新循环。在独立 Python 中，你首先创建 `SimulationApp`，然后导入需要 Kit 的模块并从脚本中调用更新。将包装器视为运行时的一部分：它设置捆绑的 Python 模块、扩展和本机库的路径。普通的机器学习 virtualenv 可以具有相同的 Python 主要版本和次要版本，但仍然缺少这些路径或暴露冲突的库。将仿真器进程和外部 Jazzy 工具保留在规定的环境中。跨越进程边界的 ROS 消息具有有线合同。将本机 Python 模块导入 Kit 具有额外的二进制兼容性契约。 [NVIDIA 独立 Python](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/python_scripting/manual_standalone_python.html) · [NVIDIA ROS 设置](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_ros.html)

根据你需要观察的内容选择你的工作方式。当你需要交互式检查变换和碰撞器时，视口非常高效。独立脚本使配置和退出状态更容易重现。支持的 Linux 容器可以打包用户空间依赖项以进行可重复部署，但主机驱动程序和 GPU 暴露仍然参与其中。远程 GPU 主机将昂贵的工作从笔记本电脑上移走，但代价是资产和日志的另一个副本边界。顶点重放在 CPU 上非常有用，可在安排 GPU 访问时执行读取器和数据合约。 [NVIDIA容器安装](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_container.html) · [桌面顶点](/zh/notes/capstone-tabletop/)

## 实验室·一次验证一层

1. 下载适合你操作系统的 6.1.0 工作站存档。遵循 NVIDIA 的提取和 `post_install` 步骤。在解压的安装目录中打开终端。 [发布下载](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/download.html) · [工作站设置](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_workstation.html)
2. 针对你的平台运行以下命令。在兼容性检查器中，运行Test Kit（测试 Kit）并记录其结果。在打开完整的应用程序之前关闭检查器。

   ```bash
   # Linux, from the extracted installation
   cat VERSION
   nvidia-smi
   ./isaac-sim.compatibility_check.sh
   ./isaac-sim.sh
   ```

   ```powershell
   # Windows PowerShell, from the extracted installation
   Get-Content VERSION
   nvidia-smi
   .\isaac-sim.compatibility_check.bat
   .\isaac-sim.bat
   ```

3. 为首次运行着色器编译留出时间。创建一个新舞台，然后从“创建”→“物理”添加一个地平面，从“创建”→“灯光”添加一个远光，从“创建”→“形状”添加一个立方体。将立方体移至平面上方。选择立方体后，记录其大小和初始垂直平移。在“属性”面板中，使用“添加”→“物理”→“带有碰撞体预设的刚体”。按“播放”并检查是否有一个可见的立方体掉落并停留在平面上。观察其静止时的垂直位姿。这会向 Kit 启动检查添加视口和物理检查。 [NVIDIA基础使用教程](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/introduction/quickstart_isaacsim.html)
4. 关闭应用程序。在解压的安装中将下面的可运行程序保存为 `smoke_isaac.py`。在 Linux 上运行 `./python.sh smoke_isaac.py` 或在 Windows PowerShell 中运行 `.\python.bat smoke_isaac.py`。提供的包装器设置仿真器的运行环境。在导入套件扩展之前初始化 `SimulationApp`。

   ```python
   from isaacsim import SimulationApp

   app = SimulationApp({"headless": True})
   try:
       app.update()
       print("Headless app update completed")
   finally:
       app.close()
   ```

检查站。将构建、GPU 和驱动程序、Test Kit（测试 Kit）结果、桌面观察和无头退出状态放在一起。在 Bash 中，在命令之后立即捕获 `$?`。在 PowerShell 中检查 `$LASTEXITCODE`。无头消息确认应用程序更新，退出状态检查进程已成功完成。使用 [场景实验室](/zh/notes/isaac-scene/) 验证引用的机器人资产是否已解析，并使用 [桥实验室](/zh/notes/isaac-ros-bridge/) 验证传感器输出。 [NVIDIA独立Python](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/python_scripting/manual_standalone_python.html)

## 预测、改变和解释立方体测试

选择一个你可以推理的高度。对于以米为单位、Z 轴向上的说明性舞台，以及以 1.10 m 为中心的未缩放的 0.20 m 立方体，立方体的底部从平面上方 1.00 m 开始。在重力为 9.81 m/s² 的理想自由落体中，需要 √(2 × 1.00 / 9.81) ≈ 0.45 模拟秒才能到达平面。如果它平着地，它的中心应该停留在 0.10 m 附近。这些都是预测。求解器以离散步骤前进，接触具有容差，并且经过的墙时间包括图形和调度。在添加精确的计时断言之前，使用高度和稳定的最终位姿作为验收标准。

保存简单阶段的副本。播放停止后，使用立方体的碰撞属性禁用立方体的碰撞器，并启用其刚体。将其重置为相同的位姿并回放。预测重力仍然会移动它，但飞机将不再阻止它。如果它消失，请遵循其 Z 平移，而不是假设它渲染失败。恢复对撞机，从相同的位姿重新启动，并再次验证立方体是否静止。这为你提供了同一运行中可见网格、移动刚体和缺失接触的已知示例。当一个更复杂的对象稍后出现在表中时，你已经知道要检查哪些属性。

## 从第一个失败的行开始调试

| 说明性记录 | 下一步区分检查 |
| --- | --- |
| 设备枚举失败 | 首先检查主机上的GPU和驱动程序。如果主机通过但 Linux 容器失败，请检查 GPU 如何暴露给该容器。 |
| 设备已列出，Test Kit（测试 Kit）失败 | 将确切的设备和驱动程序与矩阵进行比较。读取第一个渲染器或扩展初始化错误并保存启动日志。 |
| Test Kit（测试 Kit）通过，桌面启动停滞 | 让首次运行的着色器进行编译并检查日志以了解进度。在得出吞吐量结论之前与第二次启动进行比较。 |
| 立方体在游戏过程中可见且静止 | 检查物理启用、立方体的动态主体设置和播放状态。灯光控制阴影，对重力没有影响。 |
| 无头包装器成功退出，引用的机器人为空 | 检查美元参考和资产根配置。检查是否可以从仿真器主机或容器内部解析资产。 |

每次尝试保留一个记录，包括启动命令、启动时间、第一个诊断错误和观察到的结果。在更改设置之前保留失败记录。例如，对于资产访问问题，保留已知良好的原始阶段并在更正资产根后重新运行它。然后再次打开引用的示例。已修复的参考和仍在工作的基元隔离了对你更改的边界的改进。 [NVIDIA资产设置](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/accessing_assets.html)

## 练习题及解答

远程 Linux VM 在 `nvidia-smi` 中看到其 NVIDIA A100。为无头相机实验室选择它是否足够？

<details>
<summary>检查你的答案</summary>
<p>6.1.0 要求不包括没有 RT 核心的 GPU，包括 A100。为相机实验室选择支持的 GPU。确认 GPU 可见性、套件启动和实际图像捕获作为单独的探针。你可以在等待该主机时在 CPU 上运行 capstone 重放。</p>
</details>

一位同事的桌面应用程序通过了多维数据集测试。他们的无头脚本在打印任何带有导入错误的内容之前失败，并且其日志中的命令是来自训练 virtualenv 的 `python smoke_isaac.py`。你会首先运行哪两项检查？

<details>
<summary>检查你的答案</summary>
<p>使用安装的 Python 包装器运行相同的文件并检查第一个异常。如果它现在到达 Kit 但扩展导入失败，请检查导入顺序。将初始化放在需要运行应用程序的导入之前。如果应用程序启动，请保留原始和更正的启动命令作为证据。更改 GPU 驱动程序将使导入路径假设未经检验。</p>
</details>

## 常见的误解

- 一次成功启动即可证明工作站。启动冒烟测试涵盖初始化。吞吐量、资产访问和相机捕获需要其他组件的工作。
- 容器拥有每个依赖项。映像承载用户空间组件，而主机提供驱动程序和对 GPU 的访问。
- Headless 只进行 CPU 测试。无头控制窗口。请求 RTX 渲染图像的工作负载仍然会使用 GPU 渲染器。

## 总结

固定版本和主机组合，然后设计其故障有一小部分解释的探针。原始场景将物理和渲染与资源访问隔离。无头包装器隔离脚本化的启动路径。将记录的基线带入弗兰卡实验室，这样新的场景一次会引入一类新的问题。
