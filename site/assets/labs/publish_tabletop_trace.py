"""Publish a synthetic ROS 2 trace for replay; never publish motion commands."""

import math

import rclpy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import PoseStamped, TransformStamped
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_clock
from rosgraph_msgs.msg import Clock
from tf2_ros import TransformBroadcaster


class TracePublisher(Node):
    def __init__(self):
        super().__init__("tabletop_trace")
        self.tick = 0
        self.clock_writer = self.create_publisher(Clock, "/clock", qos_profile_clock)
        self.pose_writer = self.create_publisher(PoseStamped, "/tabletop/observation", 10)
        self.tf_writer = TransformBroadcaster(self)
        self.timer = self.create_timer(0.1, self.publish_tick)

    def publish_tick(self):
        stamp = Time(sec=1 + self.tick // 10, nanosec=(self.tick % 10) * 100_000_000)
        self.clock_writer.publish(Clock(clock=stamp))
        transform = TransformStamped()
        transform.header.stamp = stamp
        transform.header.frame_id = "tabletop_base"
        transform.child_frame_id = "tabletop_sensor"
        transform.transform.translation.x = 2.0
        transform.transform.translation.y = 1.0
        transform.transform.rotation.z = math.sqrt(0.5)
        transform.transform.rotation.w = math.sqrt(0.5)
        self.tf_writer.sendTransform(transform)

        observation = PoseStamped()
        observation.header.stamp = stamp
        observation.header.frame_id = "tabletop_sensor"
        observation.pose.position.x = 1.0
        observation.pose.orientation.w = 1.0
        self.pose_writer.publish(observation)
        self.tick += 1


def main():
    rclpy.init()
    node = TracePublisher()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
