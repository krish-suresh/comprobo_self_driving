import sys
import pigpio
import time
import numpy as np 
from .geometry import AckermannState
from rclpy.node import Node
from std_msgs.msg import Float64, Int64

class AckermannDrive():
    """
    """

    def __init__(self, ros_node: Node):
        """
        """
        self.connect = pigpio.pi()
        self.ros_node = ros_node
        self.imu_sub = self.ros_node.create_subscription(Float64, "/imu_yaw", self.process_imu, 10)
        self.start_heading = None
        self.curr_heading = None
        self.encoder_sub = self.ros_node.create_subscription(Int64, "/encoder", self.process_encoder, 10)
        self.prev_encoder_ticks = 0
        self.curr_encoder_ticks = 0
        self.TOTAL_ENCODER_TICKS = 8192
        self.WHEEL_ENCODER_RADIUS = .03 # m
        self.ESC_PIN: int = 15
        self.SERVO_PIN: int = 14
        self.WHEEL_BASE: float = 0.29845 # m 11.75in
        self.MIN_WIDTH_ESC: int = 1000
        self.MAX_WIDTH_ESC: int = 2000
        self.TIRE_DIAMETER: int = 0.11      # m
        self.GEAR_RATIO: int = 42
        self.MAX_RAW_RPM: int = 10400
        self.RAD_TO_PWM = -1000/(np.pi/2)
        self.CENTER_PWM = 1250
        self.TURN_PHI_MAX = np.radians(32)
        self.TURN_PHI_MIN = np.radians(-47)
        self.MAX_VEL: float = ((self.MAX_RAW_RPM / self.GEAR_RATIO)/60) * ((self.TIRE_DIAMETER * np.pi))  # m/s
        self.state = np.array([0, 0, 0, 0, 0.01])  # x, y, theta, steer_angle, forward_speed
        self.steering_angle = 0
        self.u = np.zeros((2,1))
        self.previous_odom_time = None
        self.previous_set_input_time = None
        self.curr_heading = 0

    def process_imu(self, msg: Float64):
        yaw = -msg.data
        if not self.start_heading:
            self.start_heading = np.deg2rad(yaw)
        self.curr_heading = np.deg2rad(yaw) - self.start_heading

    def process_encoder(self, msg: Int64):
        self.curr_encoder_ticks = msg.data

    def set_steering_angle(self, phi: float):
        """
        """
        self.steering_angle = phi
        steering_pwm_signal = phi*self.RAD_TO_PWM + self.CENTER_PWM
        # print(f"Steering Angle: ", phi)
        # print(f"steering {steering_pwm_signal}")
        self.servo_pwm(width=steering_pwm_signal)

    def set_drive_velocity(self, vel: float):
        """
        """
        input_vel: float = vel / self.MAX_VEL
        # print(f"Drive Velocity: ", input_vel)
        # print(self.MAX_VEL)
        esc_pwm_signal = -input_vel*(self.MAX_WIDTH_ESC-self.MIN_WIDTH_ESC)/2 + self.MIN_WIDTH_ESC + (self.MAX_WIDTH_ESC-self.MIN_WIDTH_ESC)/2
        # print(f"esc {esc_pwm_signal}")
        self.esc_pwm(width=esc_pwm_signal)

    def esc_pwm(self, width: int, snooze: int = 0):
        """
        """
        self.connect.set_servo_pulsewidth(self.ESC_PIN, width)
        if snooze:
            time.sleep(snooze)
        return
    
    def servo_pwm(self, width: int, snooze: int = 0):
        """
        """
        self.connect.set_servo_pulsewidth(self.SERVO_PIN, width)
        if snooze:
            time.sleep(snooze)
        return

    def arm_esc(self):
        """
        """
        self.esc_pwm(width=self.MIN_WIDTH_ESC)
        input("Connect power and press Enter to continue...")
        self.esc_pwm(width=self.MIN_WIDTH_ESC, snooze = 4)

    def calibrate_esc(self):
        """
        """
        self.esc_pwm(width=self.MAX_WIDTH_ESC)
        input("Connect power and press Enter to continue...")
        self.esc_pwm(width=self.MAX_WIDTH_ESC, snooze=2)
        self.esc_pwm(width=self.MIN_WIDTH_ESC, snooze=4)

    def get_state(self) -> AckermannState:
        """
        Return Ackermann state
        """
        return AckermannState(self.state)

    def update(self):
        """
        update odom
        """
        # TODO replace with encoder odom
        if not self.previous_odom_time:
            self.previous_odom_time = time.time_ns()
            return
        cur_time = time.time_ns()
        delta_ticks = self.curr_encoder_ticks - self.prev_encoder_ticks
        dist_travelled = delta_ticks/self.TOTAL_ENCODER_TICKS*(2*np.pi*self.WHEEL_ENCODER_RADIUS)
        self.state[0] += dist_travelled * np.cos(self.curr_heading)
        self.state[1] += dist_travelled * np.sin(self.curr_heading)
        self.state[2] = self.curr_heading
        # self.state[3] = self.steering_angle
        # self.state[4] = dist_travelled/(cur_time - self.previous_odom_time)*10**9 + 0.01
        self.previous_odom_time = cur_time
        self.prev_encoder_ticks = self.curr_encoder_ticks

    def non_linear_dynamics(self):
        x = self.get_state().to_vector()
        L: float= self.WHEEL_BASE
        x_dot = np.zeros_like(x)
        x_dot[0] = x[4]*np.cos(x[2])  # x_dot
        x_dot[1] = x[4]*np.sin(x[2])  # y_dot
        x_dot[2] = np.tan(x[3])*x[4]/L  # theta_dot
        x_dot[3] = self.u[0]  # steer_angular_speed
        x_dot[4] = self.u[1]  # forward_accel
        return x_dot

    def get_linearized_system_matrix(self) -> np.ndarray:
        x = self.get_state().to_vector()
        # if np.all((x == 0)):
        #     x = np.array([0, 0, 0, 0, 0.2])
        # print(np.around(x, 2))
        L: float = self.WHEEL_BASE
        return np.array([[0, 0, -np.sin(x[2])*x[4], 0, np.cos(x[2])],
                  [0, 0, np.cos(x[2])*x[4], 0, np.sin(x[2])],
                  [0, 0, 0, (1/(np.cos(x[3])**2))*x[4]/L, np.tan(x[3])/L],
                  [0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0]])

    def get_input_matrix(self) -> np.ndarray:
        return np.array([[0, 0],
                         [0, 0],
                         [0, 0],
                         [1, 0],  # steering angle
                         [0, 1]])  # forward accel

    def set_control_input(self, u):
        if not self.previous_set_input_time:
            self.previous_set_input_time = time.time_ns()
            return
        self.u = u
        current_time = time.time_ns()
        t_delta: float = (current_time - self.previous_set_input_time)/ (10 ** 9)
        self.state[3:] += u*t_delta
        self.set_steering_angle(self.state[3])
        self.set_drive_velocity(self.state[4])
        self.previous_set_input_time = current_time

    def curvature_to_steering(self, k):
        if k == 0:
            return 0
        r = 1/k
        return np.arctan(self.WHEEL_BASE/r)
