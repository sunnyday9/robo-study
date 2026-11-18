---
title: "机器人系统的 CI 与可观测性"
topic: "Infrastructure"
order: "103"
description: "为每个 CI 作业提供明确的声明，并收集证据以在重放、模拟和评估中定位失败。"
prerequisites: "了解 ROS 回放和容器输入的范围如何"
minutes: 50
---

## 将工作与要求相匹配

CI 通过后有人合并了预处理更改。那天晚上的 Isaac 作业超时，LeRobot 结果似乎有所改善，因为通过评分的回合较少。一个绿色徽章就隐藏了这两个问题。为每个作业提供一个带有输入、可观察输出和失败条件的声明。你想要一个快速的作业，能够在每次更改时捕获真正的合同违规行为，再加上来自较慢作业的足够证据来定位第一次失败，而无需重新运行所有内容。

持续集成 (CI) 在指定条件下运行检查。对每次更改的 CPU 运行程序进行快速、小的检查。对于需要受支持的 GPU 和已知驱动程序的功能，请使用单独的标记 GPU 通道。让每项工作远离执行器网络。绿色 CPU 作业提供有关其输入和断言的证据。独立跟踪 GPU 结果，并具有明确的通过、失败或跳过状态。

| 巷 | 建议检查 | 需要保存的证据 |
| --- | --- | --- |
| 每次更改时的 CPU | 验证模式、单调情节时间戳、帧和动作维度以及分割不相交。在配备 ROS 的 CPU 运行器上本地回放一个小型装置。 | 检查退出状态、夹具摘要、测试报告、主题计数和时间范围。 |
| 标签 艾萨克 GPU | 在可信运行中，启动无头 Isaac Sim 6.1.0，加载固定阶段，运行固定步骤，并检查一个传感器输出和脚本控制器的结果。 | 跑步者清单、图像摘要、渲染和物理日志、种子和成功计数所有计划的试验。 |
| LeRobot离线评估 | 使用 LeRobot v0.4.3 和 Python 3.12。当策略允许时，解码保留的事件并评估 CPU 上或兼容 GPU 上的固定检查点。 | 数据集修订、分割、检查点和预处理哈希、错误单位以及事件计数和评分动作。 |

示例性 GitHub Actions 作业使用路由字段 `runs-on: [self-hosted, linux, x64, gpu, rtx]`。仅当你将 `gpu` 和 `rtx` 等自定义标签分配给合适的跑步者时，它们才会路由作业。在打开阶段之前预检实际的 GPU 和驱动程序。在具有作业超时的隔离 GPU 运行器上运行可信修订版。不受信任的拉取请求属于隔离的托管运行器。 [GitHub 运行器标签](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow)，[GitHub Actions 安全使用](https://docs.github.com/en/actions/reference/security/secure-use)。

按成本和诊断价值订购检查。畸形的装置应该会在几秒钟内失效。回放测试添加了有关主题类型、时钟和交付的证据。渲染器和控制器测试添加了有关固定场景和仿真器的证据。单独的 LeRobot v0.4.3/Python 3.12 评估可以解码示例并在声明的条件下对 PushT 策略进行评分。艾萨克·弗兰卡 (Isaac Franka) 通行证不会告诉你该策略的行动空间。跨这些系统的集成需要经过验证的适配器。在行动之前保持观察并选择一个仿真时钟，其中重放或模拟提供 ROS 时间。

## 在 CI 中运行范围固定装置检查

以下是GitHub.com的完整教学流程。将其保存为 `.github/workflows/infra-trace.yml` 到练习存储库中，该存储库在 `site/assets/labs/` 下具有现有的 [capstone 验证器](/assets/labs/check_trace.py) 和 [教学跟踪](/assets/labs/tabletop-trace.csv)。它使用 Ubuntu 24.04 托管运行器和 Python 3.12，没有任何秘密，并且不需要 ROS 或 GPU。对于团队工作流程，请针对第三方和第一方操作依赖项使用经过审核的完整提交 SHA。这里的主要标签使示例更易于阅读。 [托管运行器标签](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)、[setup-python](https://github.com/actions/setup-python)、[上传工件](https://github.com/actions/upload-artifact)。

```yaml
name: Trace fixture
on: [pull_request, push]
permissions:
  contents: read
jobs:
  trace-contract:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    defaults:
      run:
        shell: bash
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - name: Verify valid and over-budget pairings
        run: |
          mkdir -p evidence
          cd site/assets/labs
          out=../../../evidence
          { git rev-parse HEAD; python --version;
            sha256sum check_trace.py tabletop-trace.csv; } > "$out/inputs.txt"
          python check_trace.py tabletop-trace.csv 2>&1 | tee "$out/baseline.log"
          grep -Fx 'OK: 6 rows across 2 episodes' "$out/baseline.log"
          status=0
          python check_trace.py tabletop-trace.csv --max-skew-ns 1000000 \
            > "$out/tight-budget.log" 2>&1 || status=$?
          cat "$out/tight-budget.log"
          test "$status" -eq 1
          grep -Fx 'FAIL: line 3: observation-to-command skew outside budget' \
            "$out/tight-budget.log"
      - name: Save fixture evidence
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: trace-contract
          path: evidence/
          retention-days: 7
```

将负面案例与正面案例一起设计。该灯具的最大偏差为 2 毫秒。使用默认的 10 毫秒预算，预期计数为两集的六行。将预算收紧至 1 毫秒，验证器应退出 1 并给出指定的诊断。丢失的 Python 文件也会以非零值退出。要求预期原因可以防止 CI 将基础架构错误误认为成功拒绝。 GitHub 的显式 Bash shell 应用管道故障处理，因此 `tee` 保留日志而不隐藏失败的验证器。当失败时下载证据，并根据记录的装置进行复制，并在编辑断言之前提交。 [工作流 shell 行为](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)。

首先在本地运行两个 Python 调用。一旦工作流程通过，在观察之前故意将临时副本中的第二个指令时间戳移动一纳秒，并对该副本运行基线检查。预计会出现排序或倾斜失败。恢复夹具并重新运行检查。如果你想让帧对齐成为发布声明，请添加一个单独的测试，在微小的回放中将可见的移动和动作配对。 CSV 门会看到 ID 和标记，但无法判断所选图像是否与该行匹配。

## 收集证据缩小过错范围

使用 **logs**来处理离散事件，例如丢失纹理或不兼容的订阅者。为每个记录提供一个阶段、运行 ID、情节 ID（如果适用）以及带有时钟源的时间戳。使用 **metrics**进行计数和分布，例如丢帧、峰值 VRAM 和 p95 解码延迟。将分母和单位放在每个结果旁边。使用 **traces**在捕获、传输、解码和评估过程中跟踪一个样本。使用样本或跟踪 ID 关联跨度。使用进程内的单调运行时间，并在跨主机进行比较时考虑时钟偏移。 [开放遥测信号](https://opentelemetry.io/docs/concepts/signals/)。

保存已解析的启动参数、提交、主机清单、版本、工件哈希、种子以及成功和失败运行的通过条件。每次使用一个更改的输入与上次运行进行比较。固定种子可提高设置内的可重复性。跨平台和设备，选择数字检查的容差并保持离散不变量的精确性。 [PyTorch 重现性](https://docs.pytorch.org/docs/2.7/notes/randomness.html)。

假设你有 33 毫秒的处理预算和来自本地回放过程的一个说明性示例。使用单调计时器来记录该过程中已完成的工作。单独保留源采集标记以进行对齐。

```text
 episode B / frame 17        elapsed wall time from arrival
 arrive        decode starts  decode ends        command emitted
   0 ms ------------ 19 ms ------ 27 ms -------------- 41 ms
          queue wait          decode           inference + send
           19 ms               8 ms                  14 ms
                                            ^
                                       budget at 33 ms
```

该示例超出了 8 毫秒的预算。队列等待是其最长的间隔。仅将 8 毫秒解码优化一半会达到 37 毫秒，但仍然会失败。测量每个区间在多个样本中占主导地位的频率。较小的队列可以减少陈旧帧，但代价是丢弃。更快的消费者可以保留帧，但可能需要更多计算。以相同的速率重复相同的回放两次以估计运行变化，然后更改一个因素，例如队列深度。比较延迟、截止日期错过和丢失。如果进程在不同的主机上运行，​​请按情节和帧或跟踪 ID 加入并使用本地跨度持续时间，直到有有限的时钟偏移。 ROS 仿真时钟可以暂停或跳转，适用于样本语义，而单调计时器适用于经过的挂墙时间。

从围绕入队、解码、推理和动作发射的应用程序开始。在已配置 `ros2_tracing` 和 LTTng 的 Linux Jazzy 主机上，启动 `ros2 trace --session-name infra-replay --list`，按 Enter 开始捕获，然后在另一个终端中启动微型重放，并在运行后停止跟踪。在节点初始化之前启动会保留用于将事件映射到节点的元数据。比较回调开始和结束时间，并将它们加入到仪器提供共享 ID 的应用程序事件中。仅 ROS 跟踪可能会忽略 GPU 工作或在检测回调之外等待的时间。使用小跟踪窗口并在禁用跟踪的情况下比较相同的工作负载以检查扰动。 [Jazzy追踪教程](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Advanced/ROS2-Tracing-Trace-and-Analyze.rst)。

## 用分母报告可靠性

在启动前定义运行群体和通过规则。一个说明性的套件计划 20 次弗兰卡重置。第 15 次任务成功，第 2 次任务失败，第 3 次超时。结果是 **15/20**，超时仍然可见。报告 15/17 将奖励系统超时。离线损失仍然可以改进其评分子集，因此请报告评分计数以及无法解码的数量。对于定时门，提前定义人口、单位和阈值。例如，记录所有调度帧中有多少命令满足 33 毫秒预算，然后报告已完成命令中的 p95，以及单独的丢失计数。将重试视为新的尝试并保留原始结果和日志。如果嘈杂的跑步者主导方差，请在计时检查门合并之前修复环境或设置基于证据的界限。

## 实验室·让一个小故障自己解释

在 Bash 中运行此 Python 3 标准库检查。它使用两个合成回放记录，不需要 ROS、ML 包、GPU 或机器人。它检查一集中的时间戳顺序。

```bash
python3 - good <<'PY'
import json
import sys

run_id = "fixture-" + sys.argv[1]
stamps_ns = [0, 33_000_000 if sys.argv[1] == "good" else 0]
for sample, (previous, current) in enumerate(zip(stamps_ns, stamps_ns[1:]), 1):
    if current <= previous:
        print(json.dumps({
            "run_id": run_id, "stage": "replay", "episode": "demo-1",
            "sample": sample, "error": "non_increasing_timestamp",
            "previous_ns": previous, "current_ns": current,
        }), file=sys.stderr)
        raise SystemExit(1)
print(json.dumps({
    "run_id": run_id, "stage": "replay",
    "samples": len(stamps_ns), "status": "pass",
}))
PY
```

**Checkpoint.**好的案例报告两个样本并退出零。将第一行更改为 `python3 - bad <<'PY'` 并重新运行整个块。预计退出 1 并识别情节、从零开始的样本索引以及来自 stderr 的两个时间戳值。然后绘制一条链接该行的跟踪以进行捕获和解码，以便你可以区分重复的输入数据和转换错误。

## 练习

<details>
<summary>自检 · CPU 检查通过，但 GPU 作业产生零相机帧。你从哪里开始？</summary>
<p>检查GPU探针和仿真器启动日志，然后阶段资产分辨率、模拟进度、相机配置和输出权限。 CPU 架构检查无法确定渲染器是否已运行。根据实际发生的情况保留失败或跳过的 GPU 结果。</p>
</details>

<details>
<summary>转移 · 队列丢弃 100 个样本中的 15 个，其余全部在预算内完成。这能通过 95% 的截止日期目标吗？</summary>
<p>不会。观察到的截止日期成功率为 85/100，因为丢弃的样本在截止日期前未生成任何命令。报告 15 次丢弃以及 85 次完成的延迟分布。使用相同的订购固定装置和速率独立比较更大的队列和更快的消费者。选择同时满足延迟和完整性标准的变体。</p>
</details>

## 常见的误解

- **“绿色 CI 表示机器人可以工作。”**每项检查仅支持对其运行装置和固定装置执行的索赔。
- **“更快的 p95 证明系统得到了改进。”**检查其总体以及丢弃或超时的案例，然后得出更多样本满足截止日期的结论。
- **“日志时间戳告诉我推理花费了多长时间。”**在工作中使用单调跨度。保留源时间戳以进行观察和操作对齐。

## 总结

将一份数据合同转变为小型正负 CI 测试。保存失败时的输入和结果，以便你可以重现它。对于较慢的车道，追踪第一个分歧样本，单独更改可疑原因，并报告针对预先声明的群体的时间和成功情况。

对于[桌面顶点](/zh/notes/capstone-tabletop/)，按照从ROS回放到模拟拾放再到离线模仿评估的顺序附上证据。如果没有经过验证的适配器，请使用受支持的 LeRobot 数据集并报告该数据集的离线结果。离线操作误差衡量记录观测结果的一致性。任务完成需要闭环部署。
