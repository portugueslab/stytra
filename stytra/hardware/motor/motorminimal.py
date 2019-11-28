from stytra.hardware.motor.stageAPI import Motor
from time import sleep

acc = int(204552 / 10)
velo = int(107374182 / 10)

# motor_y = Motor(1, scale=1)
# motor_y.open()
# motor_y.homethatthing()
# sleep(6)
# motor_y.diablechannel()
# sleep(5)
# motor_y.enablechannel()
# motor_y.movethatthing(432211)

# motor_y.homethatthing()
# motor_y.open()
# motor_y.setvelocity(acc, velo)
# motor_y.close()
# sleep(5)
#
# motor_x = Motor(2, scale=1)
# motor_x.homethatthing()
# motor_x.open()
# motor_x.setvelocity(acc, velo)
# motor_x.close()
#
motor_x = Motor(2, scale=1)
motor_x.open()

motor_x.get_homing_params()
motor_x.set_homing_reverse(1)
motor_x.homethatthing()
# motor_x.homethatthing()
# motor_x.setvelocity(acc, velo)
# sleep(6)
# motor_x.diablechannel()
# sleep(5)
# motor_x.enablechannel()
# motor_x.movethatthing(432211)

