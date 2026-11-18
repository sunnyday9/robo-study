---
title: "机器人系统与嵌入式控制"
topic: "Field engineering"
order: "120"
description: "将移动机器人分为主机、微控制器和电机驱动器，然后测试命令流静音时会发生什么。"
prerequisites: "Python 函数和基本反馈循环。该实验室需要 Python 3 和终端。"
minutes: 50
---

## 决定当主机停止时什么必须继续工作

<figure class="lesson-figure">
  <a href="/assets/figures/embedded-boundaries.svg"><img src="/assets/figures/embedded-boundaries.svg" width="640" height="387" loading="lazy" decoding="async" alt="主机将目标发送到微控制器。微控制器检查并终止目标，向驱动器发送命令，并独立于主机接收本地车轮反馈。"></a>
  <figcaption>实线箭头为命令；虚线箭头是反馈。这显示了控制所有权，而不是接线或安全级保护电路。</figcaption>
</figure>

室内移动机器人有两个驱动轮。它的主机估计姿态，规划路线，并发送所需的前进速度和偏航率。车轮半径为 `r`，接触轨道宽度为 `b`（以米为单位），理想的防滑车轮目标是 `left = (v − bω/2) / r` 和 `right = (v + bω/2) / r`（均以弧度/秒为单位）。正轮速推动火星车前进。对于 `v = 0.20 m/s`、`ω = +0.40 rad/s`、`r = 0.05 m` 和 `b = 0.30 m`，目标是 `2.8` 和 `5.2 rad/s`。在 `base_link` 向前 X、向左 Y 和向上 Z 的惯例中，右轮左转时行驶得更快。滑动和有效半径会改变实际产生的运动。 [ROS REP 103](https://raw.githubusercontent.com/ros-infrastructure/rep/master/rep-0103.rst) · [坐标系](/zh/notes/coordinate-frames/)

当相机分配帧或规划器搜索拥挤的地图时，计算这些目标的过程可能会停止。即使在失速期间，微控制器 (MCU) 也可以对编码器进行采样、调节轮速并在本地时钟上终止主机命令。驱动器提供并调节电机功率。一些驱动器已经关闭电流和速度环路，在这种情况下，MCU 可以监控目标和反馈，而不是重复这些环路。给每个循环一个所有者。对于教学移动机器人，主机每 20 毫秒发送一次车轮目标，MCU 每 5 毫秒检查一次，建模命令租约在最后接受的接收事件后 50 毫秒到期。通过分析实际设计的动态和故障路径来选择这些速率。

```text
 Host: planner -> wheel targets -- commands --> MCU: validate -> speed control
                  diagnostics <-- telemetry --      ^                 |
                                                     |                 v
                                wheel encoder counts +-- wheels <-- motor drive

 Independent protective path --------------------------> drive inhibit, if designed for it
 MCU local clock ----------------> expire stale commands even if host is silent
```

箭头显示两条反馈路径。编码器反馈位于速度环本地，而遥测则通知主机。即使主机或 MCU 停止执行，单独设计的保护路径也能解决危险。决定保护路径必须做什么是机器风险评估的一部分。扭矩抑制可以允许滑行，并且当扭矩消失时，桌面臂可以掉落负载。单独的软件标志并不能提供关于这两种结果的证据。

## 根据你需要的信息选择接口

有刷直流齿轮电机可以使用具有占空比和方向接口的兼容驱动器。占空比设置开关周期的一小部分，因此与轮速的关系取决于电源电压、负载和反馈。无刷电机需要一个能够处理换向的驱动器，这意味着按顺序切换其相位。智能驱动器可以公开电流或速度目标并报告限制和故障。对于每个候选者，请阅读目标的含义、如何发出饱和信号、复位对输出有何作用以及通信丢失如何改变驱动器状态。检查组件级别的工作电压、连续和瞬态电流、热包络和反馈兼容性。

增量正交信号通过两个通道上的转换顺序对运动进行编码。硬件正交计数器可以在 CPU 处理其他工作时累积转换。记录计数约定、齿轮比、计数器宽度和每个轮子的方向。如果编码器电机每转生成 12 个正交周期，则按 30:1 缩减的 x4 解码会给出车轮每转的 `12 × 4 × 30 = 1,440` 计数。对于 `Δn` 以经过的秒数计数 `Δt`，速度为 `2πΔn / (1,440Δt)`。 5 ms 窗口中的一个计数大约代表 `0.87 rad/s`。较长的窗口会降低量化步长并增加延迟。绝对编码器在启动时报告其指定范围内的位置，并引入其自身的有效性、延迟和回绕行为。与普通计数器翻转分开跟踪重新启动。 [Microchip正交解码器数据手册](https://ww1.microchip.com/downloads/en/DeviceDoc/70208B.pdf) · [PID反馈](/zh/notes/pid-feedback/)

| 接口 | 当它适合时 | 失败签名和下一个证据 |
| --- | --- | --- |
| CAN | 多个低速率控制设备共享一条总线。预算仲裁、有效负载开销和流量突发。 | 错误计数上升、低优先级流量等待或控制器进入总线关闭状态并停止参与。比较设备状态、帧年龄和应用程序序列差距。恢复的接口仍然需要新的命令会话。 |
| 串口 | 附近的点对点外设交换适度的字节流。指定波特率和具有完整性检查和重新同步功能的有界消息格式。 | 帧错误或接收溢出可能会显示为损坏的应用程序消息。将外围设备错误计数与解析器拒绝和重新同步时间进行比较。 |
| 以太网与IP | 主机需要高带宽传感器或结构化遥测。明确选择传输方式。 | 链接可以与套接字丢失或队列建立共存。 TCP 按顺序重新传输和传递字节，这可能会延迟丢失数据后面的新命令。 UDP 可能会丢失或重新排序数据报。记录应用程序边界处的序列间隙和接收年龄。 |

对于任何这些接口，成功的发送都是本地证据。设计反馈，报告接受了哪个命令以及应用了哪个目标。定义一个有界的最新值切换，其中取代命令有意义。为故障和重置事件保留单独、明确的路径。 [Linux SocketCAN](https://docs.kernel.org/networking/can.html) · [Microchip USART 特性](https://onlinedocs.microchip.com/oxy/GUID-EDB1839B-8CB3-4792-92DA-B3964E0885C3-en-US-5/GUID-D2A30854-6913-4802-9DFE-CD35D2A8A64D.html) · [TCP 规范](https://www.rfc-editor.org/rfc/rfc9293.html#section-2.2) · [UDP 规范](https://www.rfc-editor.org/rfc/rfc768.html)

## 分别预算能源和瞬态负载

在示例性的 12 V 稳压总线上，驱动器的平均电流为 4 A，计算和传感器的平均电流为 1 A，总功耗为 60 W。在假设条件下，总线上的可用电量为 72 Wh，`72 Wh / 60 W = 1.2 h` 是粗略的能量估计。每个驱动器 6 A 加上 1 A 计算的单独瞬态场景要求 13 A，或 12 V 时 156 W。检查持续负载期间峰值、电池电压骤降、保护跳闸、稳压器裕度和热量的持续时间和重复情况。检查制动是否将能量返回至电源以及驱动器和电源可以吸收哪些能量。这些数字是预算审查的算术数字。组件和保护决策需要供应商数据、根据批准的计划测量的负载以及负责工程师的审查。随着每次加速而增加的重启计数器建议在重新调整控制器之前检查电源并重置证据。

## 实验室——用事件驱动状态机

在固件中，定时器或接收中断通常执行简短的工作，例如捕获时间戳和发出任务信号。该任务解析数据、维护状态并发布遥测数据。避免无界的运动命令队列，并将唤醒标志与到达计数区分开来。例如，FreeRTOS 提供来自中断上下文的直接任务通知，并支持可以合并重复事件的位标志。 [FreeRTOS 任务通知作为事件标志](https://freertos.org/Documentation/02-Kernel/02-Kernel-features/03-Direct-to-task-notifications/04-As-event-group)

将以下内容保存为 `embedded_events.py` 并运行 `python embedded_events.py`。所有时间戳都是模拟接收器本地毫秒。显式的arm事件建立一个会话并以输出零开始其初始租约。有效的递增序列更新租约。在恰好 50 毫秒时，到期优先于任何事件。标量输出是一个建模的车轮目标。真正的传输还需要一种针对延迟但增加的命令的策略，例如在已知时钟域中具有源年龄验证的有界传输路径。

```python
LEASE_MS = 50
events = {
    0: ("arm", 1, 0, 0.0),
    5: ("command", 1, 1, 2.8),
    25: ("command", 1, 2, 2.8),
    45: ("command", 1, 2, 7.0),  # Duplicate sequence.
    80: ("command", 1, 3, 2.8),  # Command after expiry.
}
session = last_valid_ms = None
sequence, target = 0, 0.0

for now_ms in range(0, 91, 5):
    if session is not None and now_ms - last_valid_ms >= LEASE_MS:
        session, target = None, 0.0
        print(f"{now_ms:2} ms expired, target={target:.1f} rad/s")
    if now_ms not in events:
        continue
    kind, epoch, seq, requested = events[now_ms]
    if kind == "arm" and session is None:
        session, sequence, last_valid_ms = epoch, 0, now_ms
        print(f"{now_ms:2} ms armed with target zero")
    elif kind == "command" and epoch == session and seq > sequence and abs(requested) <= 8.0:
        sequence, target, last_valid_ms = seq, requested, now_ms
        print(f"{now_ms:2} ms accepted seq={seq}, target={target:.1f} rad/s")
    else:
        print(f"{now_ms:2} ms rejected seq={seq}, target={target:.1f} rad/s")
```

预计在 5 毫秒和 25 毫秒时接受，在 45 毫秒时重复拒绝，在 75 毫秒时到期，在 80 毫秒时拒绝。将 45 毫秒事件更改为序列 3，并添加 100 毫秒的控制步。到期时间变为 95 毫秒，因为只有可接受的事件才续订租约。如果重复续订租约，请检查你写入最后有效时间戳的位置。该模型每个周期检查一个合成事件，并将目标状态记录在内存中。它既不测量固件响应时间也不测量停止距离。在硬件上，保护路径和安全恢复过程需要调试证据。 [调试和诊断](/zh/notes/commissioning-and-diagnostics/)

## 练习

1. 选择速度估算器。在稳定的 `0.20 rad/s` 下，5 毫秒计数差估计器会看到什么？提出 50 毫秒替代方案的测试。

<details>
<summary>解决方案</summary>

预期计数增量约为每 5 毫秒 0.23，产生的大部分为零被 `0.87 rad/s` 附近的一计数尖峰中断。 50 ms 窗口具有 `0.087 rad/s` 步长。重放恒速斜坡的量化计数，然后反转。比较稳定误差以及估计需要多长时间才能显示反转。使用这两个结果选择一个窗口。

</details>

2. 检查重新连接。过期后，传输重试会在操作员授权新运行后立即传递旧会话的命令。你将如何进行重放诊断？

<details>
<summary>解决方案</summary>

使用现有事件元组格式在相应的字典键处添加 `(85, arm session 2)` 和 `(90, command session 1, sequence 99)`。检查输出是否保持为零并且最后接受的时间保持在 85 毫秒。在 95 毫秒处添加新的会话 2 命令，并具有更长的控制步范围，以显示合法的恢复。在真实的系统中，需要在重置过程中具有明确的会话身份，并监督显式的重新配置决策。

</details>

## 总结

根据时间和故障行为分配传感、控制、监督和电源职责。写下每个边界的单位和限制。使用区分有效接收、拒绝流量和过期输出的事件跟踪来验证丢失和恢复。将时序假设带入[下一讲](/zh/notes/real-time-and-cpp/)。
