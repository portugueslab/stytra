"Testspace for functions"

from stytra.hardware.motor.stageAPI import Motor
from time import sleep


motor_x = Motor(2, scale=1)
motor_y = Motor(1, scale=1)

#open motor and set parameters if wished
motor_y.open()
motor_x.open()

#(home at first try)
# motor_x.home()
# motor_x.open()
# sleep(5)
# # motor_y.home()
# motor_y.open()
sleep(10)

acc = int(204552)
velo = int(107374182)


motor_y.setvelocity(acceleration=acc, velocity=velo)
motor_x.setvelocity(acceleration=acc, velocity=velo)
#function to test
pos_y = motor_y.get_position()
pos_x = motor_x.get_position()
print(pos_x, pos_y)

# motor_x.move_relative(20000*30)
motor_x.move_rel(20000*30)
# motor_y.movesimple(pos_x + 20000*30)
# motor_x.movethatthing(20000*30)
sleep(1)
pos_y = motor_y.get_position()
pos_x = motor_x.get_position()
print('After moving', pos_x, pos_y)
# motor_y.home()

#close motor again
sleep(5)
motor_x.close()
motor_y.close()
