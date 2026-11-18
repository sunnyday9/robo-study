---
title: "验证、故障注入与可靠性"
topic: "Field engineering"
order: "123"
description: "将命令丢失要求转变为可测试的不变量，练习错误，并保留其他工程师可以审核的证据。"
prerequisites: "调试和诊断、基本 Python 单元测试以及移动机器人命令租赁示例。"
minutes: 55
---

## 测试前写下要求

当机器人通过一次模拟时，询问进行了哪些操作以及哪些操作仍可能失败。验证检查指定的要求。验证询问最终产品是否满足其环境中的预期需求。对于移动机器人来说，“在最后接受的命令后 55 毫秒内零模型目标”是一个验证声明。移动机器人是否可以在安全操作范围内围绕人员工作，需要有关实际机器、环境及其预期用途的证据。良好的证据记录可以让下一位工程师区分这些说法。 [NASA系统工程手册，产品实现](https://www.nasa.gov/reference/5-0-product-realization/)

写入 ID、初始状态、激励、测量点、容差和故障响应。例如，要求 `CMD-01` 从具有有效非零目标的活动会话开始。如果在 50 毫秒租约到期之前没有有效命令到达，则通过 5 毫秒定期检查，建模输出必须在上次接受后 55 毫秒内为零，并保持为零，直到显式重新准备和来自新会话的有效命令为止。重复、无效值和较早的会话无法延长租约。使用接收器本地单调毫秒进行此测试。固件要求还将指定调度假设和输出观察点。 5 毫秒的裕度用于检查阶段，对于超出规定期限的迟到没有隐含的裕度。

```text
 CMD-01       input fixture + independent expected outcomes
                          |
                          v
           [controller under test] ---> observed state and timestamp
                          |                       |
                          +---------> compare <---+
                                         |
                            gate result + retained trace
```

这里的比较使用了装置的预期结果和观察到的数据。保持断言独立于控制器实现。通过调用相同的超时函数来计算预期超时的测试将在两个地方重现错误。还要检查故障发生前输出是否非零。如果你只检查最终样本，则永久卡在零的实现似乎可以处理命令丢失。

## 将每个门放在可能发生相关故障的地方

| 门 | 运行什么以及可以建立什么 |
| --- | --- |
| 纯函数和协议状态 | 使用固定装置检查钳位、符号、范围、序列处理、到期边界和重新启动行为。抓住每一个变化。 |
| 软件在环 (SIL) | 针对模拟被控对象和虚拟 I/O 运行控制器软件。测试延迟、摩擦和传感器噪声变化下的闭环行为。记录运行的工件、时间的进展情况以及被控对象遗漏的内容。下面的 Python 实验室仅对协议状态进行建模。 |
| 硬件在环 (HIL) | 在批准的设置中使用具有实时模拟被控对象和代表性接口的预期控制器硬件。这可以揭示目标 CPU、外设和协议时序缺陷。检查仿真器溢出，这样它自己错过的步骤就不会伪装成控制器故障。 |
| 监督实物验收 | 使用批准的机器程序和安装的配置来评估取决于实际机制和工作空间的效果，例如牵引力、制动响应和操作员恢复。 |

将错误注入与声明相匹配。在解析器测试过时输入处理之前删除消息。损坏解析器中的字段会测试拒绝和重新同步。直接将输出归零的模拟会绕过这两者。包括预期的阴性测试，例如重新武装后拒绝旧命令以及阳性对照。将注入的刺激限制在离线测试工具或单独批准的测试设备中。 [MathWorks SIL 和 HIL 比较](https://www.mathworks.com/discovery/hardware-in-the-loop-hil.html)

## 实验室 — 检查 CPU 上的阶段、重放和恢复

另存为 `reliability.py` 并运行 `python reliability.py -v`。该装置按规定的毫秒评估到达情况，并在到达时和每 5 毫秒控制步检查到期情况。输出是内存中的标量轮目标，以 rad/s 为单位。会话 1 最初被授权为零输出。重置会清除权限。 `arm` 事件表示测试工具已授予授权。该模型不包含物理设备，并且下面的预期窗口是独立于生成输出的代码编写的。

```python
import unittest


def simulated_targets(events):
    session, seq, last, target = 1, 0, None, 0.0
    outputs = []
    for now in range(111):
        event = events.get(now)
        if (now % 5 == 0 or event is not None) and last is not None and now - last >= 50:
            session, last, target = None, None, 0.0
        if event is not None:
            kind, epoch, number, value = event
            if kind == "reset":
                session, last, target = None, None, 0.0
            elif kind == "arm" and session is None:
                session, seq, last = epoch, 0, now
            elif kind == "frame" and session == epoch and number > seq and abs(value) <= 8.0:
                seq, last, target = number, now, value
        outputs.append(target)
    return outputs


class LeaseTests(unittest.TestCase):
    def test_valid_update(self):
        out = simulated_targets({21: ("frame", 1, 1, 2.8), 61: ("frame", 1, 2, 3.0)})
        self.assertEqual(out[20:22], [0.0, 2.8])
        self.assertEqual(out[61:], [3.0] * 50)

    def test_silence_after_off_tick_arrival(self):
        out = simulated_targets({21: ("frame", 1, 1, 2.8)})
        self.assertEqual(out[21:75], [2.8] * 54)
        self.assertEqual(out[75:], [0.0] * 36)

    def test_bad_frames_do_not_renew(self):
        out = simulated_targets({
            21: ("frame", 1, 1, 2.8),
            60: ("frame", 1, 1, 7.0),  # Duplicate.
            70: ("frame", 1, 2, 8.1),  # Out of range.
        })
        self.assertEqual(out[60:76], [2.8] * 15 + [0.0])

    def test_arrival_on_expiry_cannot_renew(self):
        out = simulated_targets({20: ("frame", 1, 1, 2.8), 70: ("frame", 1, 2, 3.0)})
        self.assertEqual(out[69:71], [2.8, 0.0])

    def test_reset_and_rearm(self):
        out = simulated_targets({
            21: ("frame", 1, 1, 2.8),
            40: ("reset", 0, 0, 0.0),
            50: ("frame", 1, 2, 2.8),
            60: ("arm", 2, 0, 0.0),
            65: ("frame", 1, 3, 2.8),
            75: ("frame", 2, 1, 2.8),
        })
        self.assertEqual(out[39:76], [2.8] + [0.0] * 35 + [2.8])


if __name__ == "__main__":
    unittest.main()
```

预计将通过五项测试。在off-tick情况下，最后一个命令在21毫秒到达，续订租约的最后期限是71毫秒，下一个tick是75毫秒。零转换发生在接受后 54 毫秒。到期到货案例测试了不同的失败。 If processing accepts the arrival at 70 ms before checking age, it extends an already expired lease. Temporarily change `>= 50` to `> 50` in a scratch copy and rerun. Expect the arrival-on-expiry test to fail even though the off-tick case can still pass.在测试其他更改之前恢复编辑。 The suite exercises outputs of this Python model. A production gate should run the real software or hardware artifact by the method named in its verification plan.

## 将测试证据转化为操作可靠性

根据要求和配置保留证据。包括控制器构建或固件哈希、参数、元素 ID、测试工具版本、种子或夹具、计时原点、通过标准、原始结果和观察到的故障原因。 Save a passing trace and a failing trace that demonstrates a test catches the intended condition.记录跳过的检查及其原因。 A change to command handling warrants rechecking lease semantics.轮胎或有效负载的改变需要审查早期的牵引力和停车证据。使用暴露分母跟踪可用性，例如声明的配置中每小时运行的故障数，并跟踪恢复时间和重复故障。

来自同一预期人群的 100 项独立试验中的零失败给出了大约 2.95% 的精确单边 95% 失败概率上限。将 `(1 − p)^100 = 0.05` 求解为 `p`。该估计取决于共同概率下的独立试验。 Running a deterministic fixture 100 times exercises repeatability within that fixture.它不提供总体水平的失败率。对于更广泛的可靠性工作，预定义工作负载组合，包括重新启动、重复操作周期和记录的配置更改。 [NIST 精确二项式置信限](https://itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbici.htm)

为值班工程师提供一份命令到期操作手册。命名警报和预期的停止或禁止状态，确定谁在批准的程序下进行控制，并在重新启动覆盖跟踪之前保留跟踪。让他们确认启动 ID、命令序列进程、拒绝计数器和上次授权的配置。离线再现，记录一项受控更改，并重复受影响的门。指定维护负责人监控连接器故障、编码器校准漂移、电池状况以及运行时间内的重复重置。更换或更改固件后，将重复的检查与已更改的依赖项联系起来。

## 练习

1.添加定时故障。本地任务在 21 毫秒接受命令后 75 毫秒跳过检查，并在 80 毫秒恢复。测试应该如何暴露它？

<details>
<summary>解决方案</summary>

让线束抑制该灯具的 75 毫秒滴答声。如果没有进一步到达，则记录每毫秒的输出，直到 80 毫秒。第一个零是接受后 59 毫秒。独立预言机应该会失败 `CMD-01`，因为输出在 76 毫秒时仍然非零。在为目标系统声明相同的限制之前，请调查调度界限或独立定时的保护机制。

</details>

2. 决定重复哪些证据。替换 MCU 通过了纯协议门，但集成试运行显示间歇性重置。最后一次物理验收使用的是原板。你记录什么状态以及你首先调查什么？

<details>
<summary>解决方案</summary>

记录协议通过、集成试运行故障以及等待更换配置的物理验收。保存板卡和固件 ID、正常运行时间、重置原因、供应遥测数据（如果可用）以及重置前的流量。将最后通过的配置与当前配置进行比较，并在隔离测试设置下重现。解决原因后，重复受影响的集成门，并将证据提交给主管，然后再继续。

</details>

## 总结

在运行测试之前定义通过标准。使用协议检查、SIL、HIL 和监督验收来检查每个人都可以观察到的故障。保留版本化证据，使用独立的预言机注入故障，并将操作手册和维护检查与获得认可的配置相关联。
