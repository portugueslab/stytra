from stytra.hardware.motor.stageAPI import Motor
from time import sleep

acc = int(204552 / 10)
velo = int(107374182 / 10)

motor_y = Motor(1, scale=1)
motor_y.open()
motor_y.motorminimal()
sleep(4)
motor_y.set_jogmode(2,1)
motor_y.set_jogstepsize(10000)
motor_y.get_jogstepsize()
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
motor_x.motorminimal()
sleep(4)
motor_x.set_jogmode(2,1)
motor_x.set_jogstepsize(10000)
motor_x.get_jogstepsize()
# sleep(2)
# print ("mov rel")
# motor_x.move_rel(-10000)

motor_x.jogging(-30000)
motor_y.jogging(40000)

# def assess_direction(number):
#     """direction 1 - forward, direction 2- reverse"""
#     if number < 0:
#         direction =1
#     else:
#         direction =2
#     return int(direction)
#
# direction = assess_direction(-3)
#
# flag = True
#
# for i in range(jogs):
#     while flag == True:
#         motor_x.movejog(direction)
#         sleep(0.2)
#         print ("done")
#         flag = False
#     flag = True


# sleep(2)
# print ("mov absolute")
# motor_x.abs_pos(21000)
# motor_x.move_absolute()


# motor_x.get_homing_params()
# motor_x.set_homing_reverse(1)
# motor_x.homethatthing()
# motor_x.homethatthing()
# motor_x.setvelocity(acc, velo)
# sleep(6)
# motor_x.diablechannel()
# sleep(5)
# motor_x.enablechannel()
# motor_x.movethatthing(432211)

