import rclpy
from samplechanger_interfaces.srv import MoveToPosition

def move_robot_to_position(position_name):
    rclpy.init()
    node = rclpy.create_node('move_to_position_client')
    client = node.create_client(MoveToPosition, 'move_to_position')
    while not client.wait_for_service(timeout_sec=1.0):
        pass
    request = MoveToPosition.Request()
    request.position_name = position_name
    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future)
    result = future.result()
    node.destroy_node()
    rclpy.shutdown()
    return result.success, result.message