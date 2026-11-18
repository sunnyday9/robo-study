---
title: "选择并调试 ROS 2 通信接口"
topic: "ROS 2"
order: "062"
description: "选择主题、服务或操作并诊断发现的端点无法交换数据的原因。"
prerequisites: "正在运行的 Jazzy 工作区和心跳实验室。"
minutes: 35
---

## 解释一个没有任何内容的可见主题

你的仿真器的预览主题出现在 ROS 图中，但感知节点没有接收到任何帧。偶尔重新启动似乎会有所帮助。在更换节点之前，构建一个两端实验，使此症状可预测。目标是你可以在两次试验中发现的发布者、通过某个显式 QoS 设置不接收任何内容的订阅者以及仅在更改该设置时接收样本的订阅者。然后询问如果样品到达但处理仍然落后，你会测量什么。

## 围绕可能出错的地方设计界面

一个进程可以托管多个节点。该图描述了这些节点公开的端点，包括发布者、订阅者和服务客户​​端。发现发现端点存在。为了交换主题数据，端点还需要相同的解析主题名称和消息类型以及兼容的 QoS。 `ros2 interface show std_msgs/msg/String` 显示生成的字段。对于观察和命令，类型为客户端提供了通用编码，并让工具内省字段。在其旁边写下语义契约：哪个框架描述了值，标记指的是哪个事件，以及角度是否以弧度为单位。使用相同类型的两个出版商仍然可能在这三个方面存在分歧。

| 呼叫者需要什么 | 接口 | 桌面示例 |
| --- | --- | --- |
| 观察具有零个或多个独立消费者的流 | 具有消息类型的主题 (`.msg`) | 将联合读数提供给可视化和记录器 |
| 从服务器获取简短的请求/响应 | 具有请求和响应类型的服务 (`.srv`) | 查询仿真器当前的场景ID |
| 通过反馈、取消和结果来跟踪长期目标 | 具有目标、结果和反馈类型的操作 (`.action`) | 请求模拟拾放并观察进度 |

使用主题进行观察，因为每个消费者都可以独立启动、停止和选择其交付策略。添加记录器不需要更改仿真器的应用程序代码。没有应用程序级确认规划器使用了任何特定框架。服务对于快速快照或有界查询是有意义的。 API 具有不同的请求和响应字段，但应用程序仍然需要超时策略。在超时的状态更改请求之后，你可能会得到未知的结果：服务器可能在回复丢失或延迟之前采取了行动。自动重试最容易证明读取或故意幂等突变的合理性。

模拟选秀可能需要几秒钟并提前停止。当调用者必须跟踪该生命周期时使用操作。目标可以承载目标位姿，反馈可以报告活动阶段，结果可以报告终端状态和测量的放置误差。在轮询结果之前处理拒绝。将取消接受与最终状态分开处理。服务器可以接受一个目标，然后中止它。 ROS 将这些消息与目标相关联，并使用下面的服务和主题来实现协议。一个简单的命令主题将让你设计目标标识、状态、取消和结果关联。长同步服务将生命周期问题转移到阻塞的调用者身上。 [ROS 2 接口](https://docs.ros.org/en/jazzy/Concepts/Basic/About-Interfaces.html) · [ROS 2 动作设计](https://design.ros2.org/articles/actions.html)

## 在增加队列深度之前交付的原因

服务质量 (QoS) 描述发布者提供的内容以及每个订阅者请求的内容。可靠的发布者可以尽力满足请求。尽最大努力的报价无法满足可靠的请求。挥发性持久性适合后期加入者可以等待下一个样本的流。瞬时本地持久性允许实时发布者保留也请求瞬时本地持久性的后期加入订阅的样本。静态转换在发布很久之后就很有价值。昨天的相机框架通常是无关紧要的。两者都是主题，具有不同的保留和交付需求。

通过保留最新历史记录，深度限制了端点保留的样本数量。假设帧以 30 Hz 到达，一名工作人员每帧需要 80 毫秒。在这个简化的估计中，工作线程可以处理 12.5 帧/秒，留下大约 17.5 帧/秒的缺口。队列可能会吸收短突发，但持续的过载最终会导致帧丢失、增加寿命或根据设置产生背压。较大的历史记录无法修复 QoS 不匹配问题。对于预览流，接受帧丢失并仅保留最近的工作可能更可取。对于需要完整序列的数据集编写器，测量损失并提供吞吐量或限制源。仅可靠的交付并不能保证每个应用程序回调都按时完成。 [Jazzy QoS 兼容性表](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html)

## 实验室——让一个可见的主题失败

打开两个 Bash 终端并在两个终端中输入 `~/robo_ws/lab-env.bash`。在 A 中启动一个合成发布者。修复主题名称、消息类型、速率和负载，以便可靠性实验有一个自变量。 [终端设置](/zh/notes/ros2-workspaces/)

```bash
ros2 topic pub --rate 2 --qos-reliability best_effort \
  /tabletop/sample std_msgs/msg/String '{data: preview}'
```

在终端 B 中，检查图表并依次尝试每个可靠性策略。

```bash
ros2 topic list -t
ros2 topic info -v /tabletop/sample
timeout 5s ros2 topic echo /tabletop/sample std_msgs/msg/String \
  --once --qos-reliability reliable
timeout 5s ros2 topic echo /tabletop/sample std_msgs/msg/String \
  --once --qos-reliability best_effort
```

期望可见的发布者提供尽力而为、超时的可靠回显以及来自尽力而为回显的 `data: preview`。记录所提供的策略和每次回显的结果。五秒是本地实验室的诊断预算，因此还要确认在进行比较时 A 已经在发布。如果发布者不存在，请首先比较域和发现设置。如果两次尝试都挂起，请验证 A 是否仍在发送，并且解析的名称和类型是否正确。如果两者都成功，请在得出结论之前检查第二个出版商。

从另一侧重复一次。保持 B 的可靠探头固定，使用 `--qos-reliability reliable` 重新启动 A，然后重复探头。现在它应该收到 `preview`。这隔离了要约和请求之间关系的不兼容。应用程序需求决定了实际系统中应该更改哪个端点。使用 Ctrl+C 停止发布者。 [Jazzy主题CLI源码](https://github.com/ros2/ros2cli/tree/jazzy/ros2topic/ros2topic/verb)

## 当端点匹配并且回调停止时

rclpy 执行器运行准备工作，例如订阅回调、计时器或服务响应处理程序。准备就绪使工作有资格运行。线程可用性和回调组决定它何时可以运行。在此说明性跟踪中，客户端使用单个执行程序线程。服务器在另一个进程中运行。

```text
Elapsed     Client executor                         Server
   0 ms     timer enters, sends request, waits      receives request
   8 ms     still in timer                          sends reply
  10 ms     next timer is due, reply is ready        idle
 100 ms     still waiting for the reply handler     idle

After changing only the client to send-and-return:
   0 ms     timer sends request, returns            receives request
   8 ms     can handle ready reply on arrival       sends reply
  10 ms     eligible to run next timer              idle
```

即使回复正确到达客户端，第一个时间线也可能发生。唯一的执行器线程仍然被等待者占用。在 rclpy 中，实体默认为节点的互斥回调组。添加线程同时保留该组中的等待计时器和客户端仍然可以阻止响应处理。单独的组和可用线​​程可以允许并发，但会付出共享状态同步的代价。首先避免回调内的等待。 [爵士回呼组指南](https://docs.ros.org/en/jazzy/How-To-Guides/Using-callback-groups.html)

这是客户端节点模式的核心。假设 `self.client` 是 `std_srvs/srv/Trigger` 客户端，`Trigger` 是从 `std_srvs.srv` 导入的，`self.pending` 以 `None` 开头。使用定时器调用`poll_server`。此摘录假设一个单线程执行器。

```python
def poll_server(self):
    if self.pending is not None or not self.client.service_is_ready():
        return
    self.pending = self.client.call_async(Trigger.Request())
    self.pending.add_done_callback(self.on_reply)


def on_reply(self, future):
    self.pending = None
    try:
        reply = future.result()
    except Exception as exc:
        self.get_logger().error(f'service reply failed: {exc}')
        return
    self.get_logger().info(f'success={reply.success}: {reply.message}')
```

返回让响应处理继续进行。挂起的守卫可以防止快速计时器淹没缓慢的服务。必须从丢失回复中恢复的应用程序还需要截止日期、清理未完成的请求以及针对未知结果的策略。诊断停顿时，记录单调回调进入和退出时间以及回复完成情况。如果你的昂贵操作是 ML 推理，请使用其采集时钟来测量处理持续时间和使用时输入的寿命。在添加工作人员之前绑定待处理的工作。对于许多预览管道，采用最新可用帧的工作人员通过放弃被取代的工作来保持较低的输入年龄。单独的进程还可以隔离受 CPU 限制的 Python 工作并提供独立的调度，但代价是需要另一个数据传输和进程来监视。

## 练习

1. 调试两个不同的档位。相机订阅者看到尽力而为的发布者并且不会收到任何帧。安装兼容探针后，该探针会接收帧，但应用程序中的计时器在请求服务后仍然停止。哪些证据应该触发每个修复？

<details>
<summary>解决方案</summary>
<p>将相机报价与应用程序的要求进行比较，并通过单设置回波实验验证匹配情况。用于计时器、日志请求、回调返回和完成。如果执行器陷入同步调用中，请异步发送并从计时器返回，以便可以调度回复。独立的回声执行对其自己的订阅的交付。它几乎没有提及应用程序的执行者。</p>
</details>

2.设计拾取界面。操作员想要取消正在进行的模拟拾取，而可视化器和记录器需要每个可用的进度观察。命名接口并说出你要测试的内容。

<details>
<summary>解决方案</summary>
<p>对选取生命周期使用操作。单独验证接受的目标是否可以完成以及取消请求是否可以达到适当的最终结果。如果独立消费者需要机器人观察，请发布带有记录单位和印章的键入状态主题。在负载下测试刻录机是否存在间隙，并相应地选择其 QoS 和源速率。行动反馈生命周期涵盖目标客户，而观察主题则支持独立消费者。</p>
</details>

## 常见的误解

- 图表可见性证明了交付。检查解析的名称、类型和两个端点的策略，然后观察示例。
- 更深的队列修复了缓慢的回调。它给工作提供了等待的地方。比较测量的样品年龄和增加深度之前的处理能力。
- 返回的球门手柄证明成功。检查验收情况，然后检查最终结果。他们回答不同的问题。

## 总结

根据调用者需要观察或控制的内容选择接口。分别证明发现、匹配和交付。消息到达后，使用回调计时和输入期限来区分执行程序停顿和吞吐量问题。

接下来，使用 [ROS 2 帧和时间](/zh/notes/ros2-frames-and-time/) 为流附加含义。
