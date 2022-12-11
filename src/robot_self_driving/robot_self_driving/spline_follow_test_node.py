import rclpy
from rclpy.node import Node
from drive_commands.msg import DriveCommand
from .robot import Robot
from .geometry import AckermannState
from .curves import CubicSpline2D
from .trajectory import CubicSplineTrajectory, TrapezoidalMotionProfile
import numpy as np

class SplineFollowTestNode(Node):
    def __init__(self):
        super().__init__('waypoint_test_node')
        timer_period = 0.05

        self.timer = self.create_timer(timer_period, self.run_loop)
        self.robot = Robot(self, use_sim=True)
        # self.robot.drive.arm_esc() # TODO figure out way to detect if already on and only arm if power is off
        xp = [0, 0.5, 1, 0]
        yp = [0, 0, 1, 1.5]
        sp = CubicSpline2D(xp, yp)
        mp = TrapezoidalMotionProfile(sp.s[-1],2,1)        
        trajectory = CubicSplineTrajectory(sp, mp)
        self.robot.controller.follow_trajectory(trajectory)

    def run_loop(self):
        self.robot.update()
        if self.robot.controller.is_following:
            print(self.robot.drive.get_state())
        else:
            print("Path following ended.")
        

def main(args=None):
    rclpy.init(args=args)
    node = SplineFollowTestNode()
    rclpy.spin(node)
    rclpy.shutdown()