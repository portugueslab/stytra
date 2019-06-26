import numpy as np
from stytra.hardware.motor.stageAPI import Motor
from stytra.hardware.video.cameras.spinnaker import SpinnakerCamera
import cv2
from time import sleep


class MotorCalibrator():

  def __init__(self, m1, m2):
      self.motti1 = m1
      self.motti2 = m2

      # self.cam = SpinnakerCamera()
      # self.cam.open_camera()
      # self.cam.set("exposure", 12)

  def calibrate_motor(self):
      self.point_x_prev, self.point_y_prev = MotorCalibrator.find_dot(self)

      posx = self.motti2.get_position()
      self.motti2.movethatthing(posx + 20000) #20000 motot units is 1 mm
      print("movedone")
      sleep(0.5)
      posy = self.motti1.get_position()
      self.motti1.movethatthing(posy + 20000) #20000 motot units is 1 mm
      print("movedtwo")
      sleep(0.5)
      self.point_x_after, self.point_y_after = MotorCalibrator.find_dot(self)

      self.distance_points_x = int(self.point_x_prev - self.point_x_after)
      self.distance_points_y = int(self.point_y_prev - self.point_y_after)
      print(self.distance_points_x, self.distance_points_y)

      self.conversion_x = int(20000/ abs(self.distance_points_x))
      self.conversion_y  = int(20000/ abs(self.distance_points_y))

      print ("conversion factors x,y: ", self.conversion_x, self.conversion_y)

      return self.conversion_x, self.conversion_y


  def find_dot(self):
      # print("opening")
      # self.cam = SpinnakerCamera()
      # self.cam.open_camera()
      # self.cam.set("exposure", 12)
      # print("opened")

      image_converted = self.cam.read()
      cv2.imshow("img",image_converted)
      cv2.waitKey(50)

      #identify dot
      blobdet = cv2.SimpleBlobDetector_create()
      keypoints = blobdet.detect(image_converted)
      kps = np.array([k.pt for k in keypoints])

      self.center_y = 270 #maybe change hardcoding and get info from camera directly
      self.center_x = 360

      self.point_x = int(kps[0][0])  #change: what will happen with more than one dot?
      self.point_y = int(kps[0][1])

      self.distance_x = int(self.center_x - self.point_x)
      self.distance_y = int(self.center_y - self.point_y)
      print("kps: {}".format(kps))

      # self.cam.cam.EndAcquisition()

      return self.point_x, self.point_y

  def calculate(self, x, y):
      center_y = 270
      center_x = 360

      distx = int(center_x - x)
      disty = int(center_y - y)

      # distx = abs(distance_x)
      # disty = abs(distance_y)
      connx = int(distx * 1538)  # get from calibrator later
      conny = int(disty * 1538)  # get from calibrator later

      return connx, conny , distx, disty



  def track_dot(self):#, pos_x, pos_y, connx, conny, distance_x, distance_y):
      pos_x = self.motti2.get_position()
      pos_y = self.motti1.get_position()
      print ("stage at x,y:",pos_x, pos_y)

      conx = abs(self.distance_x)
      connx = int(conx * 1818)#  self.conversion_x) #some over/undershooting through rounding errors
      cony = abs(self.distance_y)
      conny = int(cony * 1666) # self.conversion_y) #some over/undershooting through rounding errors
      print (connx, conny)


      if self.distance_x > 0:
          conn = (pos_x + connx)
          # self.motti2.movethatthing(conn)
          self.motti2.movesimple(conn)

      if self.distance_x < 0:
          conn = (pos_x - connx)
          # self.motti2.movethatthing(conn)
          self.motti2.movesimple(conn)

      if self.distance_y > 0:
          conn = (pos_y + conny)
          # self.motti1.movethatthing(conn)
          self.motti1.movesimple(conn)

      if self.distance_y < 0:
          conn = (pos_y - conny)
          # self.motti1.movethatthing(conn)
          self.motti1.movesimple(conn)

  def track_dot_mini(self, pos_x, pos_y, connx, conny, distance_x, distance_y):

      if distance_x > 0:
          conn = (pos_x + connx)
          # self.motti2.movethatthing(conn)
          self.motti2.movesimple(conn)

      if distance_x < 0:
          conn = (pos_x - connx)
          # self.motti2.movethatthing(conn)
          self.motti2.movesimple(conn)

      if distance_y > 0:
          conn = (pos_y + conny)
          # self.motti1.movethatthing(conn)
          self.motti1.movesimple(conn)

      if distance_y < 0:
          conn = (pos_y - conny)
          # self.motti1.movethatthing(conn)
          self.motti1.movesimple(conn)

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

      self.motti1.close()
      self.motti2.close()
      #return im


#############################################################################

if __name__ == "__main__":
    mottione = Motor(1)
    mottitwo = Motor(2)

    mottione.open()
    mottione.homethatthing()
    mottitwo.open()
    mottitwo.homethatthing()

    m = MotorCalibrator(mottione, mottitwo)
    m.calibrate_motor()
    # m.find_dot()
    #
    # mottitwo.movethatthing(2220000)
    # mottione.movethatthing(2220000)
    #
    # m.find_dot()
# # m.find_dot()
# # m.track_dot()
#
# #m.positions_array(70,70)
# #m.scanning_whole_area(acc,velo)
# #
# while True:
#     m.find_dot()
#     m.track_dot()
#
    mottitwo.close()
    mottione.close()

