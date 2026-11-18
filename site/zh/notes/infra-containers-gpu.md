---
title: "容器、GPU 与可复现的运行环境"
topic: "Infrastructure"
order: "101"
description: "固定 OCI 图像，逐层检查 GPU 访问，并运行具有可观察输入和输出的无头仿真器。"
prerequisites: "从环境章节了解哪个主机运行每个工具"
minutes: 50
---

## 定义可重复运行

周五的模拟写了一个相机框架。周一看起来相同的命令成功退出，结果目录为空。在更改控制器之前，确定是否运行相同的程序、输入阶段和硬件路径。你的目标是一个启动记录，用于标识图像、平台、GPU、输入和结果文件，以及在预期输出丢失或无效时失败的测试。从一个小的 CPU 映像开始学习释放循环，然后将相同的推理应用于 GPU 执行。

## 图像保留了什么

开放容器计划 (OCI) 映像打包用户空间文件和启动元数据。在本机 Linux 上，正在运行的容器使用主机内核。该映像可以固定你的 ROS 包、Python 库和仿真器二进制文件。 GPU 执行仍然取决于主机驱动程序、容器运行时的 GPU 集成以及实际分配给作业的设备。

```text
 Source + locked base + dependencies
                |
              build
                v
         image digest + platform
                |
                v
 Host driver -> container process <- read-only input revision
                |
                +--> result directory + logs (persistent)
                +--> cache (record cold or warm)
```

该过程中的箭头解释了为什么一张图像的两次启动可能会有所不同。使用标签查找版本，然后保存不可变的 `repository@sha256:…` 引用和平台，例如 `linux/amd64`。标签可以移动。多平台摘要可以识别其条目选择不同清单的索引。本地映像 ID 标识映像配置，而注册表摘要标识清单或索引。保留最终摘要以供重新运行，并保留 Dockerfile、基本摘要和依赖项锁定文件或包快照以供重建。即使配方未更改，从滚动索引解析包的重建也可能会发生变化。 [Docker 镜像摘要](https://docs.docker.com/dhi/explore/security-concepts/digests/)，[构建实践](https://docs.docker.com/build/building/best-practices/)。

| 图层 | 记录 | 如果失败首先诊断 |
| --- | --- | --- |
| 主持人 | 操作系统、内核、GPU 型号、VRAM、驱动程序 | 发生故障的主机 `nvidia-smi` 将驱动程序或设备放在调查的首位。 |
| 容器运行时 | 引擎、GPU 集成、图像摘要和平台、分配的设备 | 如果主机看到 GPU 而 CUDA 测试容器看不到，请检查守护进程上下文、运行时配置和设备请求。 |
| 应用 | 仿真器构建或 ML 锁定文件、图形或计算后端、启动标志 | 如果两个 GPU 探针均通过，请验证 Isaac 的图形功能或 PyTorch 的实际张量放置。 |
| 外部文件 | 只读输入安装、可写输出目录、资产和数据集修订 | 在将丢失的输出解释为仿真器故障之前，请检查路径、文件哈希、挂载所有权和可用空间。 |

在本机 Linux 上，NVIDIA Container Toolkit 使主机 GPU 可用于容器。在 WSL2 上，Windows NVIDIA 驱动程序提供对 Linux 工作负载的 CUDA 访问。使用 WSL 中安装的软件的特定说明。 Isaac Sim 6.1.0 记录了其针对 Linux 的容器部署。即使仅 CUDA 的工作负载通过 WSL2 运行，也可以在该实验室中使用本机 Ubuntu。 [NVIDIA 示例工作负载](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/sample-workload.html)、[WSL 上的 CUDA](https://docs.nvidia.com/cuda/wsl-user-guide/)、[Isaac Sim 容器安装](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_container.html)。

## 构建并测试小型 OCI 映像

**Design.**使用 capstone 的 [验证器](/assets/labs/check_trace.py) 和 [教学跟踪](/assets/labs/tabletop-trace.csv)。 CSV 以整数纳秒记录模拟观察和指令时间戳。验证器检查排序和倾斜预算。两者的打包为 CI 提供了一个合成装置，无需数据集服务或 GPU 即可运行。将这两个文件和以下 `Dockerfile` 放入干净的构建目录中。小型 Python 基础练习独立于仿真器进行打包。

```dockerfile
ARG PYTHON_BASE
FROM ${PYTHON_BASE}
WORKDIR /lab
COPY check_trace.py tabletop-trace.csv ./
USER 10001:10001
ENTRYPOINT ["python", "/lab/check_trace.py", "/lab/tabletop-trace.csv"]
```

**构建并运行。**在已配置的 x86-64 Linux Docker 主机上的 Bash 中，解析一次基础。第一次拉取小的基础镜像。将已解析的引用与配方一起保留并重新用于重建。

```bash
docker pull --platform linux/amd64 python:3.12-slim
base=$(docker image inspect python:3.12-slim --format '{{index .RepoDigests 0}}')
printf '%s\n' "$base"
docker build --platform linux/amd64 --build-arg "PYTHON_BASE=$base" \
  -t infra-trace:dev .
docker run --rm --pull=never --network none --read-only infra-trace:dev
```

**观察并变化。**期望 `OK: 6 rows across 2 episodes` 并退出 0。保留图像、输入和资源并收紧一个参数。在情节 `reset-a` 的第二行中，指令时间戳为 52,000,000 ns，观察标记为 50,000,000 ns。 2,000,000 ns 的差距超出了 1,000,000 ns 的预算。预计会出现第 3 行错误并退出 1。

```bash
docker run --rm --pull=never --network none --read-only \
  infra-trace:dev --max-skew-ns 1000000
```

**调试和迭代。**如果两个运行都未启动，请检查基本分辨率、构建上下文和入口点。如果两者都通过，请确认图像包含预期文件并接受参数。如果只有严格检查失败，则恢复基线并记录这两种状态。负面情况表明门在该装置中捕获了过多的延迟。将一个微小的装置复制到图像中使烟雾测试变得独立。将大型或频繁更改的阶段放在只读装载上以重用应用程序映像，然后将装载的文件视为版本化输入并在启动时检查哈希值。挂载还可以隐藏存储在映像中同一路径的文件。

## 实验室 · 一次证明一层

使用本地 Docker 守护程序和预加载的验证映像在已配置的本机 Ubuntu NVIDIA 计算机上运行这些 Bash 命令。瞬态容器仅运行 GPU 库存命令。拉取策略需要本地映像，并且容器已禁用网络。 [Docker 运行选项](https://docs.docker.com/reference/cli/docker/container/run/)。

```bash
nvidia-smi
docker image inspect nvcr.io/nvidia/cuda:12.8.0-base-ubuntu24.04 \
  --format '{{.Os}}/{{.Architecture}} {{json .RepoDigests}}'
docker run --rm --pull=never --network none --runtime=nvidia --gpus all \
  nvcr.io/nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi
```

**Checkpoint.**比较两个清单中的 GPU UUID 和驱动程序。丢失的映像是一个配置缺口。容器内列出的 GPU 确认了可见性，但未测试渲染和应用程序执行。如果你缺少此主机，请使用该表记下预期的观测结果并将探测标记为已跳过。

在多 GPU 计算机上，通过仅将设备请求更改为带有清单中 UUID 的 `--gpus "device=GPU-…"` 来缩小探测范围。仅期望选定的设备，然后返回原始请求以确认差异。显式记录设备分配，因为容器内的 CUDA 序号可能与主机的编号不同。

对于已配置的 Isaac Sim 6.1.0 容器，NVIDIA 在容器 **内记录了以下命令**。在开始场景之前保存兼容性报告。

```bash
./isaac-sim.compatibility_check.sh --/app/quitAfter=10 --no-window
```

无头作业仍然可以渲染相机并消耗 VRAM。加载一个小阶段，推进有限数量的模拟步骤，并验证一个预期的帧或状态文件是否位于主机输出目录中。也在那里捕获标准输出和仿真器日志。为缓存提供自己的可写挂载，以便你可以比较冷启动和热启动。检查容器用户是否可以写入挂载。 NVIDIA 的 `runheadless.sh` 示例开始直播。对于批处理作业，请使用该版本的独立工作流程。 [Isaac Sim 容器启动和安装](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_container.html)、[Isaac Sim 独立 Python](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/python_scripting/manual_standalone_python.html)。

假设你的程序每四个物理步骤显式渲染一次，物理配置为 60 Hz。如果预算为 120 步且没有初始捕获，预计需要 2 秒的仿真时间和 30 次渲染调用。这些是时间表的预测。如果你观察到 120 个步骤和零个渲染调用，请调查步进和节奏。如果有 30 个渲染调用但序列化帧为零，请检查传感器准备情况、序列化错误和输出权限。仅将渲染间隔更改为每两步，预测 60 个调用，并比较计数器、输出和挂起时间。将预热与稳定状态分开，并在将时间差异归因于额外渲染之前保持缓存条件可比较。

对于桥接运行，请在发送操作之前记录观测结果，并指定一个仿真时钟。 Isaac Franka 烟雾测试和 LeRobot PushT 实验室具有不同的数据和行动合同。加入它们需要一个显式的适配器。

## 通过消化释放和恢复

从经过审查的源修订版本中构建一个候选程序，然后执行打包程序及其负面案例。在发布工作流程中，将候选者发布到批准的注册表并解析其实际清单或索引摘要，例如在候选者引用上使用 `docker buildx imagetools inspect`。在目标平台上测试注册表摘要并验证发布运行程序可以解析外部输入。在相关 CPU 和 GPU 门通过后，提升相同的摘要。晋升时的重建会创建一个需要自己证据的新候选解。保存源修订、平台、基础摘要、工件修订、测试日志和先前的工作版本摘要。通过恢复旧的摘要 **和 **兼容阶段和配置输入进行回滚，然后重复有界烟雾测试。使用相同的检查将基础更新安排为有意更改。 [注册表图像检查](https://docs.docker.com/reference/cli/docker/buildx/imagetools/inspect/)。

## 练习

<details>
<summary>自检 · CUDA 探针通过，但 Isaac 相机从未发出帧。调查证实了什么？</summary>
<p>运行时将 GPU 暴露给测试容器。检查 Isaac 兼容性报告、图形驱动程序功能、RTX 和 VRAM 要求，以及场景加载和高级程度是否足以渲染。在更改映像或驱动程序之前保留日志。</p>
</details>

<details>
<summary>转移 · 发布标签连夜转移。哪些证据可以让你重复昨天的跑步？</summary>
<p>使用昨天的最终注册表摘要和平台以及确切的阶段修订和启动配置。确认主机和驱动程序兼容并检查预期输出。 Dockerfile 和基本摘要解释了镜像的构建方式。在重建过程中，单独的配方就可以解决不同的操作系统包或轮子。</p>
</details>

## 常见的误解

- **“无头意味着没有图形。”**离屏相机仍然可以渲染和使用 VRAM。
- **“绿色进程退出证明输出存在。”**检查已安装的输出并验证其内容。
- **“该图像消除了平台差异。”**即使使用固定图像也可以记录平台和分配的设备。

## 总结

建立一个具有已知正面和负面案例的小型候选解。固定其内容和输入，然后按顺序验证主机、运行时和应用程序。提升经过测试的摘要并保留回放或回滚所需的输入。

使用图像摘要、阶段资源修订和 GPU 探测状态在 [桌面 capstone](/zh/notes/capstone-tabletop/) 中进行模拟拾取和放置。运行使用虚拟传感器和执行器。
