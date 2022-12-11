import rclpy
from rclpy.node import Node
from drive_commands.msg import DriveCommand
from .robot import Robot
from .geometry import AckermannState
from .curves import CubicSpline2D, RaceTrack
from .trajectory import CubicSplineTrajectory, TrapezoidalMotionProfile, RotationLimitedMotionProfile
import numpy as np
import os

class SplineFollowTestNode(Node):
    def __init__(self):
        super().__init__('waypoint_test_node')
        timer_period = 0.05

        self.timer = self.create_timer(timer_period, self.run_loop)
        self.robot = Robot(self, use_sim=True)
        # self.robot.drive.arm_esc() # TODO figure out way to detect if already on and only arm if power is off
        print(os.getcwd())
        track = RaceTrack("/home/ksuresh/comprobo_self_driving/src/robot_self_driving/tracks/IMS_raceline.csv", 12.5, 7)
        sp = track.create_spline()
        # mp = TrapezoidalMotionProfile(sp.s[-1],2,1)        
        mp = RotationLimitedMotionProfile(sp,2,5,3,0.01)
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