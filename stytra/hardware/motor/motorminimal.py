from stytra.hardware.motor.stageAPI import Motor
from stytra.hardware.motor.motor_calibrator import MotorCalibrator
import json

acc = int(204552 / 10)
velo = int(107374182 / 10)

motor_x = Motor(1, scale=1)
motor_x.homethatthing()
motor_x.open()
motor_x.setvelocity(acc, velo)
motor_x.close()

motor_y = Motor(2, scale=1)
motor_y.homethatthing()
motor_y.open()
motor_y.setvelocity(acc, velo)
motor_y.close()

# motor_calib = MotorCalibrator(motor_x, motor_y)
# conx, cony = motor_calib.calibrate_motor()
# print ("conversion factor x: {}, y: {}". format(conx, cony))

#
# data = {}
# data['params'] = []
# data['params'].append({
#     'acceleration': acc,
#     'velocity': velo,
#     'conversion': (conx, cony)
# })
#
# with open('stage_config.txt', 'w') as outfile:
#     json.dump(data, outfile)
