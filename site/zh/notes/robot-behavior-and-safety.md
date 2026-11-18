---
title: "机器人行为与安全"
topic: "Planning and autonomy"
order: "053"
description: "构建一个小型任务执行程序来处理过时的感知、错过最后期限和命令丢失，然后测试其不变量。"
prerequisites: "导航系统和 Python 函数和类。"
minutes: 55
---

## 决定机器人下一步要做什么

移动机器人接受到达充电站的请求。当它正在行驶时，定位可能会变得无效，请求可能会被取消，或者任务进程可能会停止运行。任务执行者拥有目标生命周期，并决定是否计划、开始行动、等待、恢复或报告失败。它通过要求规划者和控制者开展工作、观测结果并在假设发生变化时撤销授权来协调他们。

有限状态机 (FSM) 存储命名状态并使用事件和防护在状态之间移动。列出接近任务的转换。从 `IDLE` 开始，仅从接受的目标和有效输入开始。在 `DRIVING` 中，前提条件的丢失优先于名义完成。到达目标区域请求停止并转换到 `STOPPING`。新的静止观察允许 `DONE`。从锁定故障中恢复需要在了解原因后进行显式重置。这使得有关同时发生的事件的决策在一处可见。

```text
 IDLE -- accepted goal --> DRIVING -- in goal region --> STOPPING
                              |                            |
                              |                     standstill seen
                              |                            v
                   invalid input or deadline             DONE
                              v
                         FAULT (latched)
                              ^
                              +--- STOPPING can fault too

 DRIVING renews a command lease. Without renewal, the receiver requests zero.
```

第一行跟踪正常进度。两种活动状态都可能发生故障。当执行者停止滴答并且根本无法转换时，接收者的到期规则也适用。

## 选择故障和中断的表示方式

行为树 (BT) 通过勾选根来评估节点。叶子可以报告成功、失败或运行。序列由连续的步骤组成，回退在失败后尝试替代分支。这适合具有可重用子树的任务，例如“到达海湾”和“等待一条畅通的路径”。检查精确控制节点的语义。在BehaviorTree.CPP 中，反应式序列可以在稍后的异步操作仍在运行时重新检查条件，而标准序列可以在该正在运行的子级处恢复。使操作可取消。停止自己计算的节点必须连接到树外部的取消、确认和命令所有权。 [BehaviorTree.CPP 反应式和异步行为](https://behaviortree.dev/docs/tutorial-basics/tutorial_04_sequence/)

FSM 使转换顺序和最终状态易于审计。当行为共享子步骤和恢复选项时，BT 会有所帮助。如果旧动作超过了转换的寿命，则任何一种设计都可能意外地发出两个运动命令。使用稳定的目标标识符、单一动作所有者以及在取消或取代后拒绝最新结果和命令的方法。围绕每个异步操作设置时间和重试预算。已请求的操作、已接受的操作和已完成的操作是不同的知识状态。 [ROS 2 操作](/zh/notes/ros2-communication/)

## 编写转换之前的状态不变量

不变量是在整个执行过程中都应该保持的属性。对于此移动机器人，要求执行程序仅在任务正在驾驶、输入是新的且任务截止日期尚未到期的情况下发出非零运动请求。接收方仅在其租约有效时接受非零请求。错误在以后的良好观察中保持锁定状态。只有通过新的静止观察才能成功完成进场。指定每个不等式的时钟域和边界规则。最后期限限制了任务的完成。看门狗检测到预期活动的缺失。即使有用的工作被楔入，仅从计时器派生的心跳也可以持续到达，因此定义更新所证明的内容。

故障安全设计需要确定系统对特定故障的响应并进入降低风险的状态。请求的零速度和观察到的静止是不同的。有些危险需要经过验证的受控停止或保持负载。作为 Python 条件实现的停止函数取决于执行过程、输入有效性、通信和下游控制器。安全级架构需要针对机器危险和适用要求评估和验证从传感和逻辑到执行器响应的完整安全功能。它可能需要一个独立的安全相关通道，具有自己的诊断和经过验证的时序。下面的练习是应用程序级模拟。在合格的监督下调试任何物理系统，并采取适当的保护措施和经过验证的停止功能。 [ISO 13849-1:2023范围](https://www.iso.org/standard/73481.html)

## 实验室：从确定性计划中删除任务流程

另存为 `executive.py` 并运行 `python executive.py`。所有时间值都是一个合成单调时钟上的整数毫秒。一次调用 `tick` 即可处理当前示例。布尔值 `stopped` 代表在本实验室中扫描的同一样本中测量到的静止状态。接收器被建模为时间和最后命令的单独函数。在保留执行滴答的同时调用它会导致进程停顿。在已部署的系统中，计时功能需要真正独立的调度边界以及经过验证的时钟和传输行为。

```python
from dataclasses import dataclass

MAX_AGE, LEASE, DEADLINE = 80, 100, 500


@dataclass(frozen=True)
class Command:
    speed: float             # m/s
    expires_ms: int


def receiver_speed(command, now):
    return command.speed if now < command.expires_ms else 0.0


class Executive:
    def __init__(self, start_ms):
        self.state = "DRIVING"  # one goal accepted by the simulated caller
        self.deadline = start_ms + DEADLINE
        self.reason = ""

    def tick(self, now, sample_ms, goal=False, stopped=False):
        if self.state in {"DRIVING", "STOPPING"}:
            if not 0 <= now - sample_ms <= MAX_AGE:
                self.state, self.reason = "FAULT", "stale input"
            elif now >= self.deadline:
                self.state, self.reason = "FAULT", "deadline"
            else:
                if self.state == "DRIVING" and goal:
                    self.state = "STOPPING"
                if self.state == "STOPPING" and stopped:
                    self.state = "DONE"
        speed = 0.20 if self.state == "DRIVING" else 0.0
        expires = min(now + LEASE, sample_ms + MAX_AGE + 1, self.deadline)
        return Command(speed, expires)


executive = Executive(0)
last = executive.tick(20, 10)
assert receiver_speed(last, 90) == 0.20
assert receiver_speed(last, 91) == 0.0  # no executive tick
assert executive.state == "DRIVING"
print("stall: receiver requests zero at 91 ms")

assert executive.tick(120, 10).speed == 0.0
assert executive.tick(140, 140).speed == 0.0
assert (executive.state, executive.reason) == ("FAULT", "stale input")
print("resumed tick:", executive.state, executive.reason)

executive = Executive(0)
assert executive.tick(100, 99, goal=True).speed == 0.0
assert executive.state == "STOPPING"
assert executive.tick(130, 130, stopped=True).speed == 0.0
assert executive.state == "DONE"
print("goal with standstill:", executive.state)

executive = Executive(0)
last = executive.tick(499, 499)
assert receiver_speed(last, 499) == 0.20
assert receiver_speed(last, 500) == 0.0
assert executive.tick(500, 500, goal=True, stopped=True).speed == 0.0
assert (executive.state, executive.reason) == ("FAULT", "deadline")
print("goal at deadline:", executive.state, executive.reason)
```

接收方在 91 毫秒时丢弃请求，因为观察是在 10 毫秒时进行的，并且在 80 毫秒（含）期间仍然有效。该命令也会在任务截止日期之前到期，并且独立地在其最大租约到期之前到期。在每个边界的两侧测试一个控制步。在模拟中，记录目标 ID、转换原因、首次错误输入时间、命令到期、零请求时间以及实际停止时间。注入旧消息、恢复期间任务取消以及失控反馈。如果主管的日志显示已停止，但模拟的轮子仍在转动，则跟踪从命令接受到测量响应的过程。

## 练习

1. 较早目标的延迟数据包在该目标被取消并接受新目标后到达。扩展接收者合约，以便较早的非零命令即使其租约仍然有效也无法生效。

<details>
<summary>解决方案</summary>

为每个运动授权指定一个纪元，并为每个命令指定该纪元的序列号。接收方仅接受其当前授权的纪元和大于最后接受的序列。撤销会废弃纪元并丢弃存储的命令。通过在撤销后从旧纪元传递实时命令进行测试，然后在新纪元内传递重新排序的命令。原来的过期检查仍然适用。

</details>

2. 演示一个案例，其中租约（而不是观测数据时延或任务截止日期）是第一次超时。然后，当接收者在到达时错误地开始租约时，比较到期时间。

<details>
<summary>解决方案</summary>

对于本实验，将 `MAX_AGE` 更改为 200。在 `now = sample_ms = 20` 中，三个候选到期时间为 120、221 和 500 毫秒。断言接收器在 119 ms 处请求运动，在 120 ms 处请求零。在 90 毫秒时下达命令。到达时开始新的租约会将其延长至 190 毫秒，隐藏 70 毫秒的传输延迟。在共享时钟假设下保留原始到期时间。

</details>

## 总结

执行人员应该使守卫优先级、取消和完成可观察。当行政人员保持沉默时，独立执行的最后期限或租约可以撤回命令。将故障痕迹和物理停止行为与名义任务成功分开进行测试，并将安全级保护视为系统工程责任。
