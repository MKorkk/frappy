from frappy.core import Command, Readable, Parameter, StringType
from .ros2_client import move_robot_to_position

class MoveRobotModule(Readable):
    position = Parameter(datatype=StringType(), default="home")

    @Command(StringType(), result=None)
    def move_to(self, position_name):
        """Move robot to a named position via ROS2"""
        success, message = move_robot_to_position(position_name)
        if not success:
            raise Exception(f"Move failed: {message}")
        self.position = position_name