import numpy as np
from stytra.hardware.motor.stageAPI import Motor
from stytra.experiments.tracking_experiments import TrackingExperiment
from stytra.hardware.video.cameras.spinnaker import SpinnakerCamera
import cv2
from stytra.calibration import CircleCalibrator


class MotorCalibrator():

  def __init__(self):
      pass

  def scanning_whole_area(self, acc, velo):

      #Gives new positions to the motor for scanning and triggers camera
      mottione.setvelocity(acc, velo)
      mottitwo.setvelocity(acc, velo)

      positions_h2 =[]

      for pos in self.positions_h:
          for posi in self.positions_w:
              print ("y:", pos, ",x:", posi)
              positions_h2.append(pos)
              mottitwo.movethatthing(pos)
              mottione.movethatthing(posi)

      mottione.close()
      mottitwo.close()
      #stack arrays w and h2 together for full coordinates of stage array
      #duplicate positions_2 *len(positions_h)
      #results_array =np.hstack((positions_h2,self.positions_w)) #not the right solution

  def scan_for_traingle(self):
      pass

  def find_dot(self): #, someparams=something):

      #get image from camera
      cam = SpinnakerCamera()
      cam.open_camera()
      cam.set("exposure", 12)
      image_converted = cam.read()
      cv2.imshow("img",image_converted)
      cv2.waitKey(600)

      #identify dot
      blobdet = cv2.SimpleBlobDetector_create()
      keypoints = blobdet.detect(image_converted)
      kps = np.array([k.pt for k in keypoints])
      print (kps)

      self.center_y = 270
      self.center_x = 360

      self.point_x = int(kps[0][0])
      self.point_y = int(kps[0][1])

      self.distance_x = int(self.center_x - self.point_x)
      self.distance_y = int(self.center_y - self.point_y)

      print("dot points x,y: ", self.point_x, self.point_y)
      print("distance x,y to center:", self.distance_x, self.distance_y)

      return self.point_x, self.point_y

  def track_dot(self):
      pos_x = mottitwo.get_position()
      pos_y = mottione.get_position()
      print ("stage at x,y:",pos_x, pos_y)

      conx = abs(self.distance_x)
      connx = int(conx *self.conversion_x) #some over/undershooting through rounding errors
      cony = abs(self.distance_y)
      conny = int(cony * self.conversion_y) #some over/undershooting through rounding errors

      if self.distance_x > 0:
          conn = (pos_x + connx)
          mottitwo.movethatthing(conn)

      if self.distance_x < 0:
          conn = (pos_x - connx)
          mottitwo.movethatthing(conn)

      if self.distance_y > 0:
          conn = (pos_y + conny)
          mottione.movethatthing(conn)
      if self.distance_y < 0:
          conn = (pos_y - conny)
          mottione.movethatthing(conn)

  def positions_array(self,  w, h):

      #Put in arena size and mm and get positions returned for scanning in motor units#

      self.width_arena = w
      self.height_arena = h
      self.encoder_counts_per_unit = 20000
      self.center =2200000
      self.stepsize = 200000 # will depend on camera magnification and pixel size

      # define starting point for array in top left corner
      positions_w = []
      positions_h = []

      start_w = int(self.center - (w*self.encoder_counts_per_unit/2))
      start_h = int(self.center + (h*self.encoder_counts_per_unit/2))
      end_h = int(self.center - (h * self.encoder_counts_per_unit / 2))

      for pos_w in range (start_w, w*self.encoder_counts_per_unit, self.stepsize):
          positions_w.append(pos_w)

      for pos_h in range (end_h, start_h, self.stepsize):
          positions_h.append(pos_h)

      self.positions_h = positions_h #.reverse()
      self.positions_w = positions_w
      print ("positions array build")

      #print (positions_w, positions_h)

  def calibrate_motor(self):

      self.point_x_prev, self.point_y_prev = MotorCalibrator.find_dot(self)

      posx = mottitwo.get_position()
      mottitwo.movethatthing(posx + 20000)

      posy = mottione.get_position()
      mottione.movethatthing(posy + 20000)

      self.point_x_after, self.point_y_after = MotorCalibrator.find_dot(self)

      self.distance_points_x = int(self.point_x_prev - self.point_x_after)
      self.distance_points_y = int(self.point_y_prev - self.point_y_after)

      self.conversion_x = int(20000/ abs(self.distance_points_x))
      self.conversion_y  = int(20000/ abs(self.distance_points_y))

      print ("conversion factors x,y: ", self.conversion_x, self.conversion_y)

      return self.conversion_x, self.conversion_y



#############################################################################
acc = 204552
velo = 107374182

m = MotorCalibrator()
mottione  = Motor(1)
mottitwo = Motor(2)
mottione.homethatthing()
mottitwo.homethatthing()

m.calibrate_motor()

m.find_dot()
m.track_dot()

#m.positions_array(70,70)
#m.scanning_whole_area(acc,velo)

# while True:
#     m.find_dot()
#     m.track_dot()
