import numpy as np
from stytra.hardware.motor.stageAPI import Motor
from stytra.hardware.video.cameras.spinnaker import SpinnakerCamera
import cv2
from time import sleep
import matplotlib.pyplot as plt



class MotorCalibrator():

  def __init__(self, m1, m2):
      self.motti1 = m1
      self.motti2 = m2

      # self.cam = SpinnakerCamera()
      # self.cam.open_camera()
      # self.cam.set("exposure", 12)

  def calibrate_motor(self):
      self.point_x_prev, self.point_y_prev, im = MotorCalibrator.find_dot(self)

      posx = self.motti2.get_position()
      self.motti2.movethatthing(posx + 20000) #20000 motot units is 1 mm
      sleep(0.5)
      posy = self.motti1.get_position()
      self.motti1.movethatthing(posy + 20000) #20000 motot units is 1 mm
      sleep(0.5)
      self.point_x_after, self.point_y_after, im = MotorCalibrator.find_dot(self)

      self.distance_points_x = int(self.point_x_prev - self.point_x_after)
      self.distance_points_y = int(self.point_y_prev - self.point_y_after)

      self.conversion_x = int(20000/ abs(self.distance_points_x))
      self.conversion_y  = int(20000/ abs(self.distance_points_y))

      print ("conversion factors x,y: ", self.conversion_x, self.conversion_y)

      return self.conversion_x, self.conversion_y


  def find_dot(self): #same as dot tracking method
      self.cam = SpinnakerCamera()
      self.cam.open_camera()
      self.cam.set("exposure", 12)
      #TODO initiate camera somewhere else- cant be double initiated.

      im = self.cam.read()
      cv2.imshow("img",im)
      cv2.waitKey(10)

      #identify dot
      idxs = np.unravel_index(np.nanargmin(im), im.shape)
      e = (np.float(idxs[1]), np.float(idxs[0]))
      self.point_x = e[0]
      self.point_y = e[1]
      print ("dot x,y", self.point_x, self.point_y)

      self.cam.cam.EndAcquisition()

      return self.point_x, self.point_y, im


  def calculate(self, x, y):
      self.center_y = 270
      self.center_x = 360
      # TODO  change hardcoding and get info from camera directly

      self.distance_x = int(self.center_x - x)
      self.distance_y = int(self.center_y - y)

      connx = int(self.distance_x * self.conversion_x)
      conny = int(self.distance_y * self.conversion_y)

      return connx, conny

  def track_dot(self):
      pos_x = self.motti2.get_position()
      pos_y = self.motti1.get_position()
      print ("stage at x,y:",pos_x, pos_y)

      connx, conny = MotorCalibrator.calculate(self.point_x, self.point_y)

      conx = pos_x + connx
      mottitwo.movesimple(conx)

      cony = pos_y + conny
      mottione.movesimple(cony)


  def positions_array(self,  w, h):
      #Put in arena size and mm and get positions returned for scanning in motor units#

      self.width_arena = w
      self.height_arena = h
      self.encoder_counts_per_unit = 20000
      self.center =2200000
      self.stepsize = 200000 # will depend on camera magnification and pixel size

      positions_w = []
      positions_h = []

      start_w = int(self.center - (w*self.encoder_counts_per_unit/2))
      start_h = int(self.center + (h*self.encoder_counts_per_unit/2))
      end_h = int(self.center - (h * self.encoder_counts_per_unit / 2))

      for pos_w in range (start_w, w*self.encoder_counts_per_unit, self.stepsize):
          positions_w.append(pos_w)

      for pos_h in range (end_h, start_h, self.stepsize):
          positions_h.append(pos_h)

      self.positions_h = positions_h
      self.positions_w = positions_w
      print ("positions array build")

  def scanning_whole_area(self):

      for pos in self.positions_h:
          for posi in self.positions_w:
              print("y:", pos, ",x:", posi)
              self.motti2.movethatthing(pos)
              self.motti1.movethatthing(posi)
              #im = SpinnakerCamera.read()
              # Camera needs to be initiated with exposure sometime before



#############################################################################

if __name__ == "__main__":
    mottione = Motor(1, scale=0)
    mottitwo = Motor(2, scale=0)

    mottione.open()
    mottitwo.open()

    mc = MotorCalibrator(mottione, mottitwo)
    mc.calibrate_motor()


    mottitwo.close()
    mottione.close()

