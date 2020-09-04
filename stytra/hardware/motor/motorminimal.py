from stytra.hardware.motor.stageAPI import Motor
from time import sleep
# from stytra.hardware.motor.mini_motti import Motor
acc = int(204552)
velo = int(107374182)



# motor = Motor()
# motor.open(1)
# # motor.home(1)
# motor.open(2)
# # motor.home(2)
# motor.start_polling(1)
# motor.start_polling(2)
#
# sleep(5)
# motor.move_rel(1, 5000)
# motor.move_rel(2, 5000)
# sleep(5)
#
#
# motor.stop_polling(1)
# motor.stop_polling(2)
# motor.close(1)
# motor.close(2)

#
motor_x = Motor(2, scale=1)
motor_y = Motor(1, scale=1)
sleep(1)

motor_y.open()
print("y homing")
motor_y.home()
motor_y.open()

sleep (5)

motor_x.open()
print("x homing")
motor_x.home()
motor_x.open()

pos_y=motor_y.get_position()
pos_x=motor_x.get_position()
print (pos_x, pos_y)

sleep(25)
#
# motor_x.move_rel(10000)
# motor_y.move_rel(10000)
# motor_y.movesimple((pos_y+10000))
# motor_x.movesimple((pos_x+10000))
# motor_y.move_relative((pos_y+10000))
# motor_x.move_relative((pos_x+10000))

sleep(5)


motor_x.close()
motor_y.close()

# motor_x.get_settle_params()
# motor_x.set_settle_params(time=197, settledError=20, maxTrackingError=2000, notUsed=0, lastNotUsed=0)
# print ("Updated params")
# motor_x.get_settle_params()
# motor_x.move_rel(20000)
# print ("moving x")
# sleep(10)
# motor_x.get_pos_loop_params()
# motor_x.request_pid()
# motor_x.set_pos_loop_params(pgain=100, intgain=300, intlim=50000, diffgain=1000, derivcalc=4, factor=6554,
#                             velo=1000, acc=1000)
# motor_x.get_pos_loop_params()
# #
# motor_y.move_rel(20000)
# print ("moving y")
# sleep(10)
# motor_y.start_polling()
# motor_y.request_status_bits()
# out = motor_y.status()
# print ("out", out)
# print (out[1])
# print ("done")
# motor_y.close()
# motor_x.close()

# def jogging_x(number):
#     stepsize = motor_x.get_jogstepsize()
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

# motor_x.set_jogstepsize(20000)
# motor_x.get_jogstepsize()
# motor_y.set_jogstepsize(20000)
# motor_y.get_jogstepsize()
#
# # motor_x.get_jogmode()
# # motor_y.get_jogmode()
# motor_x.set_jogmode(2,1)
# motor_y.set_jogmode(2,1)
# sleep(5)
#
# motor_x.movejog(1)
# sleep(2)

# motor_x.close()
# motor_y.close()

# motor_x.jogging(20000)
# motor_y.move_rel(1000)
# motor_y.get_homing_params()
# motor_x.get_homing_params()
# motor_x.set_homing_reverse(1)

# motor_x.motorminimal()
# motor_x.open()
# sleep(1)

# motor_y.motorminimal()
# motor_y.open()
# sleep(1)
#
#
# motor_x.move_rel(50000)
# sleep(1)
# motor_y.move_rel(50000)
# sleep(1)

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
