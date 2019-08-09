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
      # print ("dot x,y", self.point_x, self.point_y)

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
      self.center_x = self.motti1.get_position()
      self.center_y = self.motti2.get_position()
      self.stepsize = int(200000) # will depend on camera magnification and pixel size

      arena_w = (w * self.encoder_counts_per_unit)/363 #TODO self.scale from motor
      arena_h = (h * self.encoder_counts_per_unit) / 363  # TODO self.scale from motor
      self.arena = (int(arena_w), int(arena_h))

      positions_w = []
      positions_h = []

      start_w = int(self.center_x - (w*self.encoder_counts_per_unit/2))
      end_w = int(self.center_x + (w * self.encoder_counts_per_unit / 2))
      start_h = int(self.center_y + (h*self.encoder_counts_per_unit/2))
      end_h = int(self.center_y - (h * self.encoder_counts_per_unit / 2))

      for pos_w in range (start_w, end_w, self.stepsize):
          positions_w.append(pos_w)

      for pos_h in range (end_h, start_h, self.stepsize):
          positions_h.append(pos_h)

      self.positions_h = positions_h
      self.positions_w = positions_w

      return positions_h, positions_w

  def conversion(self):
      self.arena = (4800, 4800)
      self.im = np.zeros((540, 720))
      self.motor_posx = self.motti1.get_position()
      self.motor_posy = self.motti2.get_position()
      self.conx = self.motor_posx / (self.arena[0] / 2)
      self.cony = self.motor_posy / (self.arena[1] / 2)
      return self.conx, self.cony

  def convert_motor_global(self):
      motor_x = self.motor_posx / self.conx
      motor_y = self.motor_posy / self.cony

      mx = int(motor_x - self.im.shape[0]/ 2)
      mxx = int(motor_x + self.im.shape[0]/ 2)
      my = int(motor_y - self.im.shape[1]/ 2)
      myy = int(motor_y + self.im.shape[1]/ 2)

      return mx, mxx, my, myy

  def scanning_whole_area(self):

      self.cam = SpinnakerCamera()
      self.cam.open_camera()
      self.cam.set("exposure", 4)
      # TODO initiate camera somewhere else- cant be double initiated.
      self.arena = (4800, 4800)

      background_0 = np.zeros(self.arena)
      self.motor_posx = self.motti1.get_position()
      self.motor_posy = self.motti2.get_position()

      for pos in self.positions_h:
          for posi in self.positions_w:
              # print("y:", pos, ",x:", posi)
              self.motti2.movethatthing(pos)
              self.motti1.movethatthing(posi)
              im = self.cam.read()

              mx, mxx, my, myy = MotorCalibrator.convert_motor_global(self)
              print (mx, mxx, my, myy)
              background_0[mx:mxx, my:myy] = im
              sleep(1)

      self.cam.cam.EndAcquisition()

      return background_0


#############################################################################

if __name__ == "__main__":
    mottione = Motor(1, scale=338)
    mottitwo = Motor(2, scale=338)

    mottione.open()
    mottitwo.open()

    #TODO calibrator minimal + motor minimal combine
    mc = MotorCalibrator(mottione, mottitwo)
    # mc.calibrate_motor()
    pos_h, pos_w = mc.positions_array(50,50)
    print (pos_h, pos_w)
    conx, cony = mc.conversion()
    bg = mc.scanning_whole_area()
    plt.imshow(bg)
    plt.waitforbuttonpress()

    mottitwo.close()
    mottione.close()

