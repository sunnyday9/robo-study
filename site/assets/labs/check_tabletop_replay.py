"""Check that replayed observations resolve at their exact header stamps."""

import math
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener


def main():
    rclpy.init()
    node = Node("check_tabletop_replay")
    buffer = Buffer(node=node)
    listener = TransformListener(buffer, node)
    observations = {}

    def capture(message):
        stamp = Time.from_msg(message.header.stamp)
        observations[stamp.nanoseconds] = message
        if len(observations) > 100:
            del observations[next(iter(observations))]

    subscription = node.create_subscription(PoseStamped, "/tabletop/observation", capture, 10)
    deadline = time.monotonic() + 25
    checked = 0
    try:
        while rclpy.ok() and time.monotonic() < deadline and checked < 5:
            rclpy.spin_once(node, timeout_sec=0.1)
            for key, message in list(observations.items()):
                try:
                    sample = buffer.lookup_transform(
                        "tabletop_base", message.header.frame_id, Time.from_msg(message.header.stamp)
                    )
                except TransformException:
                    continue
                translation = sample.transform.translation
                rotation = sample.transform.rotation
                point = message.pose.position
                base_x = translation.x + (1 - 2 * rotation.z**2) * point.x
                base_y = translation.y + 2 * rotation.z * rotation.w * point.x
                if not (math.isclose(base_x, 2.0) and math.isclose(base_y, 2.0)):
                    raise ValueError(f"unexpected coordinates at {key} ns: {(base_x, base_y)}")
                del observations[key]
                checked += 1
                if checked == 5:
                    break
    finally:
        listener.unregister()
        node.destroy_subscription(subscription)
        node.destroy_node()
        rclpy.try_shutdown()

    if checked < 5:
        raise SystemExit(f"FAIL: checked {checked}/5 stamped poses before the wall-time deadline")
    print("OK: 5 stamped poses transform to (2, 2) m")


if __name__ == "__main__":
    main()
