"Simple homing script for motti to run at first opening or when stuck"

from stytra.hardware.motor.stageAPI import Motor
from time import sleep

motor_x = Motor(2, scale=1)
motor_y = Motor(1, scale=1)
sleep(1)

motor_y.open()
print("y homing")
motor_y.home()
motor_y.open()

sleep(5)

motor_x.open()
motor_x.set_homing_reverse(2)
print("x homing")
motor_x.home()
motor_x.open()

sleep(5)
motor_x.close()
motor_y.close()
