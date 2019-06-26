from stytra.hardware.motor.stageAPI import Motor
from stytra.hardware.motor.motor_calibrator import MotorCalibrator

import datetime
from time import sleep
# import random

# Run motorminimal before that here

# mottione = Motor(1)
#
# mo.open()
#
# mo.tolerance = 200
# distances1 = [3000, 6000, 9000, 12000, 15000, 18000, 21000, 24000, 27000, 30000, 33000, 36000, 39000, 42000, 45000, 48000, 51000 ]
#
# # for j in distances1:
# positions =[]
# time = []
#
# pos, t = mo.movethatthing(4400000)
# print (pos, t)
# time1 = []
# time2 = []
# time3 = []
# positions = []
# for i in range(5):
#     pos1 = mo.get_position()
#     positions.append(pos1)
#     start1 = datetime.datetime.now()
#     mo.movesimple(3300000)
#     time1.append((datetime.datetime.now() - start1).total_seconds())
#     sleep(0.2)
#
#     pos2 =mo.get_position()
#     positions.append(pos2)
#     start2 = datetime.datetime.now()
#     mo.stopprof()
#     time2.append((datetime.datetime.now() - start2).total_seconds())
#     pos3 =mo.get_position()
#     positions.append(pos3)
#     sleep(0.2)
#     #
#     # pos4 =mo.get_position()
#     # positions.append(pos4)
#     # start3 = datetime.datetime.now()
#     # mo.movesimple(3300000 + 20000)
#     # time3.append((datetime.datetime.now() - start3).total_seconds())
#     # sleep(0.2)
#     #
#     # pos5 = mo.get_position()
#     # positions.append(pos5)
#
# print (time1)
# print (time2)
# # print (time3)
# print(positions)

# distances = [3000, 6000, 9000, 12000]
# no_pos = 5000
#
# while True:
#     pos = mo.get_position()
#     print (pos)
#     for i in distances:
#         mo.movesimple(i)
#         # print (i)
#         if abs(pos - no_pos) <= 100:
#             #mo.stopimm()
#             mo.stopprof()
#             mo.movesimple(100)
#             sleep(0.4)
#             print ("final position reached")
#

# time =[]
# mo.tolerance = 200
# for i in range(6):
#     start1 = datetime.datetime.now()
#     mo.new_move(int(110000 + 20000))
#     time.append((datetime.datetime.now() - start1).total_seconds())
#
#     start2 = datetime.datetime.now()
#     mo.new_move(110000)
#     time.append((datetime.datetime.now() - start2).total_seconds())
#
# print (time)

#
# time =[]
# for i in range (5):
#     start = datetime.datetime.now()
#     mo.movesimple(3000)
#     # mo.movethatthing(3000)
#     time.append((datetime.datetime.now() - start).total_seconds())
#     sleep(0.2)
#     start1 = datetime.datetime.now()
#     mo.movesimple(22000)
#     # mo.movethatthing(22000)
#     time.append((datetime.datetime.now() - start1).total_seconds())
#     sleep(0.2)
#
# print (time)

################### calibrator
mottione = Motor(1)
mottitwo = Motor(1)

mc = MotorCalibrator()

mottione.open()
mottitwo.open()

conx, cony = mc.calibrate_motor()

mottione.close()
mottitwo.close()