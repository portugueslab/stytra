from stytra.hardware.motor.stageAPI import Motor
from time import sleep

acc = int(204552 / 10)
velo = int(107374182 / 10)

home = 2200000
move = (int(home - 1000000/2))
print (move)


motor_x = Motor(2, scale=1)
motor_y = Motor(1, scale=1)

motor_x.open()
motor_y.open()

motor_y.get_homing_params()
motor_x.get_homing_params()
motor_x.set_homing_reverse(1)

# motor_x.motorminimal()
motor_x.open()
sleep(1)

# motor_y.motorminimal()
motor_y.open()
sleep(1)


motor_x.move_rel(50000)
sleep(1)
motor_y.move_rel(50000)
sleep(1)

# def assess_direction(number):
#     """direction 1 - forward, direction 2- reverse"""
#     if number < 0:
#         direction =1
#     else:
#         direction =2
#     return int(direction)
#
# def jogging_x(number):
#     stepsize = 1
#     jogs = int(abs(number)/stepsize)
#
#     print ("X number input as distance", number, stepsize)
#     flag = True
#     direction = assess_direction(number)
#     print("X jogs taken {} in direction {}".format(jogs, direction))
#
#     for i in range(jogs +1):
#         while flag == True:
#             motor_x.movejog(direction)
#             flag = False
#             print ("X jogging", i)
#             sleep(2)
#         flag = True
#
# def jogging_y(number):
#     stepsize = 1
#     jogs = int(abs(number) / stepsize)
#
#     print("Y number input as distance", number, stepsize)
#     flag = True
#     direction = assess_direction(number)
#     print("Y jogs taken {} in direction {}".format(jogs, direction))
#
#     for i in range(jogs +1):
#         while flag == True:
#             motor_y.movejog(direction)
#             flag = False
#             print(" Y jogging", i)
#             sleep(2)
#         flag = True


# x_vals = [1,2,3,4,5,6, 7, 8, 9, 10]
#
# for i in x_vals:
#     jogging_x(i)
#     jogging_y(i)
#     sleep(2)
#     print ("done")
#
