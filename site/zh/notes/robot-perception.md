---
title: "从传感器读数到机器人感知"
topic: "Perception and estimation"
order: "042"
description: "从范围或深度恢复 3D 点，选择场景表示，并测量桌面分割失败。"
prerequisites: "坐标系、针孔相机投影和传感器校准。"
minutes: 55
---

## 确定下游系统需要什么

桌面机械手需要一个相对于其底座以米为单位的目标。检测器可以识别图像中的正确对象，同时给出较差的 3D 目标，因为边界框包括表格。室内移动机器人有不同的问题。它需要知道哪些附近空间是自由观察的，哪些空间包含障碍物，以及哪些观察缺失。这两个问题都从校准观察开始，并将它们转化为为特定决策设计的表示。

对于每个输出，记下消耗的帧、采集时间、单位、丢失数据的含义和空间容差。对于实验室，输出是基座坐标系中可见目标点的质心。参考是同一帧中理想可见表面的质心。对象中心或可行的抓取位姿将需要有关对象形状和手的附加信息。

## 恢复 3D 点，然后选择表示形式

在[针孔相机投影](/zh/notes/camera-projection/)中，一个像素定义了一条射线。对于校正像素 `(u, v)`，形成 `q = ((u - cx)/fx, (v - cy)/fy, 1)`。如果传感器报告轴向深度 `Z`，则相机帧点为 `Z q`。如果它报告沿同一射线的范围 `r`，则该点为 `r q / ||q||`。在水平归一化坐标 0.6 和垂直坐标 0 处，2 m 射线范围给出约 1.715 m 的前向深度。将其视为轴向深度为 2 m，误差向图像边缘增长。 ROS REP 118 定义了一个规范的深度图像，其轴向深度以浮点米为单位，另一种原始表示形式以无符号整数毫米为单位。在使用该值之前解析实际编码并检查有效性。 [ROS REP 118深度图像格式](https://github.com/ros-infrastructure/rep/blob/master/rep-0118.rst)

对于扫描框架中的平面激光雷达，角度 `a` 处的范围 `r` 给出 `(r cos(a), r sin(a), 0)`。枚举光束使用扫描的角度起点和增量。如果移动机器人在扫描期间明显移动，则使用姿态历史支持的采集时间来变换每个点。深度图像可以具有不同的采集约定，并且将其与颜色掩模相关联需要空间对齐和适当的时间戳。像素索引在其自己的相机和图像几何结构中具有意义。 [ROS LaserScan消息](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/LaserScan.msg) · [OpenCV标定和立体几何](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)

```text
Sensor origin O ----------- X .............. ?   distance along one ray
              | traversed | hit             | behind hit
                 free        occupied         unobserved

Endpoint X contributes a point to a cloud.
Origin O + the valid ray + hit X contribute evidence to an occupancy map.
```

点云保存观察到的表面坐标，可能带有颜色或描述符。有组织的云保留了像素网格，包括孔。体素网格将点分组到固定大小的 3D 箱中。下采样可以控制计算，但薄特征可能会消失或与另一个表面合并。占用表示使用观察来推理这些表面周围的空间。通过简单射线模型下的有效不透明命中，遍历的栅格接收自由证据，而命中的栅格接收占用的证据。它后面的空间仍然未知。无效样本可能是由于反射率差、缺乏立体对应或其他传感器特定条件而产生的。在决定射线是否提供自由空间证据之前解码这些条件。 [已占用、空闲和未知空间的 OctoMap 表示](https://octomap.github.io/)

## 选择基线并测量重要的错误

<figure class="lesson-figure">
  <a href="/assets/figures/sensor-to-map.svg"><img src="/assets/figures/sensor-to-map.svg" width="640" height="305" loading="lazy" decoding="async" alt="传感器光束在其穿过的细胞中提供免费证据，在标记命中处提供占据证据，并且在命中之外的细胞中不提供证据。"></a>
  <figcaption>点云记录命中位置。占用更新也使用射线，但返回后面的空间保持不变。</figcaption>
</figure>

检测将实例与位置（例如盒子）关联起来。语义分割为每个像素或点分配一个类别。实例分割还可以区分同一类别中的各个对象。当任务允许时，从几何开始。对于固定桌面，估计或测量其平面，将点保留在高度范围内，并对相邻点进行分组。学习模型可以区分具有相似几何形状的对象，但需要标记数据并在预期的照明、视点和背景下进行检查。检测框可以提出用于深度处理的区域。检查哪些像素或点实际上支持生成的目标。

对于掩码，并集交集 (IoU) 将它们的重叠区域除以它们的并集。对于检测，在声明的重叠规则下匹配预测和标签，计算精度和召回率，然后改变置信度阈值。例如，COCO 评估器报告多个 IoU 阈值的平均精度。除了图像空间分数之外，还测量任务空间错误。即使使用高掩模 IoU，一像素深度不连续性也可以将目标估计拉向不同的表面。跟踪产生有效 3D 目标的标签分数、有效目标之间的中值和尾部位置误差、空场景中的误报以及从采集到结果的时间。 [COCO参考评估器](https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/cocoeval.py)

## 实验室：找到凸起的补丁并打破深度基线

将代码片段保存为 `sensing-perception.py` 并运行 `python sensing-perception.py`。使用来自模拟高架摄像机的 8 x 4 校正深度图像。相机原点为基础坐标系中的 `(0, 0, 0.80)` m，z 轴向上。光学+X是基数+X，光学+Y是基数-Y，光学+Z指向下。所有像素共享一个采集时间和一个固定的变换。真正的顶部是在工作台上方 0.10 m。第二个装置仅更改深度测量，模拟丢失回波、桌子附近的混合回波和虚假前景回波的组合。标签保持固定。

```python
from math import dist, isfinite
from statistics import mean

pixels = {(u, v) for v in range(4) for u in range(8)}
target = {(3, 1), (4, 1), (3, 2), (4, 2)}
clean = {p: 0.70 if p in target else 0.80 for p in pixels}
shifted = clean | {(3, 1): float("nan"), (4, 1): 0.78, (7, 0): 0.70}


def base_point(pixel, depth_m):
    u, v = pixel
    return ((u - 3.5) * depth_m / 100,
            -(v - 1.5) * depth_m / 100,
            0.80 - depth_m)


def centroid(points):
    return tuple(mean(axis) for axis in zip(*points))


truth = centroid([base_point(p, clean[p]) for p in sorted(target)])
for name, image in [("clean", clean), ("shifted", shifted)]:
    valid = {p: base_point(p, z) for p, z in image.items()
             if isfinite(z) and z > 0}
    picked = {p for p, point in valid.items() if 0.04 <= point[2] <= 0.20}
    iou = len(picked & target) / len(picked | target)
    coverage = len(target & valid.keys()) / len(target)
    estimate = centroid([valid[p] for p in sorted(picked)]) if picked else None
    error = f"{1000 * dist(truth, estimate):.2f} mm" if estimate else "no target"
    print(f"{name}: depth coverage={coverage:.2f}, IoU={iou:.2f}, error={error}")
```

期望在干净的夹具上实现完美的覆盖、IoU 和零错误。在移位的夹具中，四个目标像素中只有三个具有有效深度。两个真实像素和一个干扰点通过高度带，因此 IoU 为 `2/5 = 0.40`，质心移动约 8 mm。仅凭高度范围无法隔离目标。在修改模型之前打印接受的像素坐标并验证异常值。将最小高度降低到 0.01 m 并比较 IoU 和质心误差。混合像素现在通过了，改善了掩模重叠，同时将估计值向下推低。这是评估下游系统使用的每个指标的原因。

在回放中，按会话或场景对验证示例进行分组，以避免几乎相同的相邻帧在分割中泄漏。添加对象材质、视点、照明和距离的切片。检查同一图章的叠加、点云和目标位置。具有良好几何形状的掩模移位表明配准或分割存在问题。正确的掩模和错误的 3D 位置建议在重新训练之前检查深度缩放、参考平面、帧方向和时序。将 CPU 结果保持在该合成夹具范围内。在监督调试之前评估模拟或试运行中的实际堆栈。

## 练习：使身高基线更具选择性

使用 4 邻居像素邻接，其中邻居共享一条边。移动后的夹具在原始阈值下产生哪些组？什么测试可以证明只保留最大的组是合理的？

<details>
<summary>检查结果</summary>
<p>(3,2) 和 (4,2) 处有一个两像素组，(7,0) 处有一个单像素组。保留该对可将 IoU 从 0.40 提高到 0.50，并且质心误差为 3.5 mm。使用较大的干扰物测试部分遮挡的目标和场景。最大分量规则假设所需的回报支持最大的连通区域。</p>
</details>

## 练习：解释空白障碍物图像

移动机器人回放显示帧上的零障碍点，其中明亮的窗口填充了其深度图像的一部分。那里的地图应该免费吗？你会比较窗户和内墙记录的哪些曲线？

<details>
<summary>检查调查情况</summary>
<p>将不可用的射线视为未知，除非传感器合同给出了自由空间的具体证据。比较每个区域的有效深度分数、障碍物回忆与场景几何形状以及观测数据时延。深度突然丧失且探测器置信度保持不变，则指向深度输入或其对齐。在更改地图更新程序之前比较有效范围和光线方向。</p>
</details>

## 弘扬什么

- 使用传感器的深度或范围约定进行反投影并在采集时进行转换。
- 根据消费者的需求选择掩模、点云或占用网格。明确保留未知区域。
- 跟踪场景变化条件下的 2D 质量、3D 错误、覆盖范围和延迟。 [地图和 SLAM](/zh/notes/mapping-and-slam/) 将注册的观测结果转换为持久地图。
