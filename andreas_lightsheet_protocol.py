#from multiprocessing import Process, Queue
import numpy as np
from PyQt4 import QtGui, QtCore  # (the example applies equally well to PySide)
import pyqtgraph as pg
import cv2
import time
from re import compile, findall
from os import listdir, makedirs
from datetime import datetime
from random import shuffle

import serial as com

import sys

#ADJUST PATH
sys.path.insert(0, r"C:\Users\lpetrucco\Desktop\Behavior\Dependencies")
JUMP_TO = r"C:\Users\lpetrucco\Desktop\Behavior\Exp014/"

from grating import Grating
from metadata import Metadata


class uc:
    def __init__ (self, comport, baudrate = None):
        
        self.conn = com.Serial(port=comport)
         
        if baudrate:
            self.conn.baudrate = baudrate
            
    def read (self):
        i = self.conn.read()
        v = self.convert(i)
        
        return v
        
    def write (self, what):
        self.conn.write(what.encode())
        
    def convert (self, i):
        return unpack("<b",i)[0]
        
    def __del__ (self):
        self.conn.close()
        
        
# Initialize pyboard and turn the camera off
pyb = uc('COM3')
pyb.write('off')



THE_MODULO = 11

savingPrivateRyan = []
expStart = datetime.now().strftime("%Y%m%d_%H%M%S")
expStartT = time.time()


SAVING_PATH = None 

device = 0




PLOT_THE_LAST = 300 # data points
EXPOSURE_TIME = 600
isExperimentRunning = True
SHOW_CIRCLES = False
bouts = 0
swimming = 0
appliedGain = 1
boutSawDifference = False
boutBlock = 0 
boutUnit = 75 # ms
swimmingTime = time.time()
showedGain0 = 0


#########################################
# Gray: yes/no
# Gain: normal/low
def createExperiment (base, conditions, trials_each = 4, repetitions = 4, randomize = True):
    exp  = []
    
    for _ in range(repetitions):
    
        if randomize:
            shuffle(conditions)
            
        exp += [[base]*trials_each + [i]*trials_each for i in conditions]
    
    flat = [j for i in exp for j in i]
    
    return tuple(flat)
    
 
############
## CHANGE THE EXPERIMENTAL CONDITIONS
############

#### [0] is first trial is grating speed 0
#### [5,10]*7 means that grating speed is alternating between 5 and 10 mm/s 7 times
Conditions = [0]+[5,10]*7


CurTrial = 0
MaxTrial = len(Conditions)


# create plot and curve.
# use a black pen
def uplot(y = [-1, 1], auto=False):
    plot = pg.PlotWidget()
    plot.showGrid(x=True, y=True)
    plot.setYRange(y[0], y[1])
    #if not auto:
    #    plot.disableAutoRange()
    p = pg.mkPen(width=2, color=(0,0,0))
    curve = plot.plot(pen=p, downsample=3)
    
    return plot, curve
    
def showCircles ():
    global SHOW_CIRCLES
    
    SHOW_CIRCLES = not SHOW_CIRCLES
    
def gratingview ():
    global grating
    
    #log("Gratingview was called.")
    
    grating.update()

def updateview ():
    global base, tip, borders, width, height, gratingtimer, startTime, grating, savingPrivateRyan, grating_incr, last_upd, bouts, pyb, JUMP_TO, SAVING_PATH

    
    
    if base.visible() or tip.visible() or (base.visible() and tip.visible()):
        return False
        
    if grating.aligned():
        #log("False...")
        return False
        
    if not height:
        
        
        height = np.abs(borders['tailbase'][1]-borders['tailtip'][1])
        width  = np.abs(borders['tailbase'][0]-borders['tailtip'][0])
        
        last_upd = time.time()
        
        log("Tail w: %d, h: %d" % (width,height))
        log("Grating is displayed.")
        
        startTime = time.time()
        gratingtimer.start(1)
        pyb.write('on')
        log("---------------------------")
        log("Acquisition STARTED!!!!!")
        log("---------------------------")

    #global grating
    global THE_MODULO,PLOT_THE_LAST, im,  Gsize, statusBar, curve1, curve2, curve3, data1, data2, data3, o, expStartT, cap, fn, viewtimer, gain, timestamp, framei
    global CurTrial, MaxTrial, swimming, gain_course, curve4, appliedGain, boutSawDifference, boutBlock, boutChance, boutUnit, swimmingTime, Conditions
    o += 1
    
    #if o % 7 == 0:
    #############################
    ### After 15s trial,      ###
    ###  make a 30s pause     ###
    #############################
    if time.time() > last_upd+10: 
        grating.setGratingSpeed(0)
    
    if time.time() > last_upd+20: 
        last_upd = time.time()
        
        CurTrial += 1
        
        if CurTrial < MaxTrial:
            grating.setGratingSpeed(Conditions[CurTrial])
        
         
        
            log("%s: Trial %d, Condition: %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), CurTrial, Conditions[CurTrial]))
        
    ##############################################
    ### Every 15 minutes (i.e. 10 min trials)  ###
    ###  increment the bar_size with one.      ###
    ##############################################
    #if time.time() > grating_incr+60*15:
    #    grating.setGratingSize(Gsize+1)
        
    #    Gsize = grating.getGratingSize()
    ##    log("%s: bar size changed" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    # #   grating_incr = time.time()
    
    # read video frame
    ret, img = cap.read()    
    #

    # show the metadata
    if o == 2:
        #log("File: %s" % fn)
        #log("Total frames: %d" % (int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))))
        log("Gain: %d" % gain)
        
    # show the FPS
    framei = rollMe(framei, time.time())
    
    fps = 1./(np.mean(np.diff(framei)))
    
    global showedGain0
    statusBar.showMessage("fps: %d    bouts per Trial: %.1f    exposure time: %.1f     time in trial: %d" % (fps, (bouts/(CurTrial+1.)), cap.get(15), (last_upd+20)-time.time()))

    
    speed_red = 0
    grating.setSpeed()
    #grating.setFrame(o)
        
    # if frame 
    if ret == True and CurTrial < MaxTrial: # and o % 2 == 0:
        #gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) # set to grayscale
        img = cv2.resize(img, None, fx=0.5, fy=0.5)
        #imgQ.put(gray)
        tail_trace(255-img) # tail_trace it

        
        #grating.setField(0)
        
        # If vigor > threshold, change speed
        if vigor[-1] > 0.4:
            if swimming == 0:
                bouts += 1
                swimmingTime = time.time()*1000
                
            
            swimming = 1
            

            speed_red = vigor[-1] * gain * appliedGain #* Conditions[0][1]
            grating.setSpeed(-speed_red)

            
        else:
            swimming = 0
            appliedGain = 1
     
        data3 = data3[1:]
        #data3 = np.roll(data3, -1)
        data3.append(-grating.getCurSpeed())
        
        gain_course = rollMe(gain_course, appliedGain)
        
        #timestamp = np.append(timestamp, int(round(time.time() * 1000)))
        
        # Plot every nth call the data
        if o % THE_MODULO == 0:
            curve1.setData(y=tail_sum_frames)
            curve2.setData(y=vigor)    
            curve3.setData(y=data3)
            #curve4.setData(y=gain_course)
            
        
        #dataToWrite = [timestamp[-1], tail_sum_frames[-1], vigor[-1], 10-speed_red, Goff, GR, swimming, Gsize]
    
        
        #blaFn.write("\t".join(dataToWrite.astype("str"))+"\n")
        savingPrivateRyan.append(np.array([int(round(time.time() * 1000)), tail_sum_frames[-1], vigor[-1], data3[-1], swimming, Conditions[CurTrial], appliedGain, CurTrial]))
        # Plot every nth call the data
        #if o % 7 == 0:
        #    curve1.setData(x=timestamp, y=tail_sum_frames)
        #    curve2.setData(x=timestamp,y=vigor)    
        #    curve3.setData(x=timestamp,y=data3)
            
    #elif ret == True and o % 2 != 0:
    #    pass
    
    elif ret == False and CurTrial < MaxTrial:
        log("Camera delivered no frame.")
        log("Trying to reconnect camera...")
        time.sleep(.2)
        cap = cv2.VideoCapture(device)
        log("Redo the last trial")
        CurTrial -= 1
        time.sleep(.2)
    
    # No frames left in video
    else:
        log("Trials reached.")
        log("Total time: %f" % (time.time()-startTime))
        gratingtimer.stop()
        stopAndSave() # Save data
        
        
def stopAndSave ():
    global savingPrivateRyan, gratingtimer, viewtimer, cap, grating, expStart, t2, blaFn, LAST_FISH_ID, the_fish, preface
    
    log("Total trials: %d" % MaxTrial)
    log("Total time [s]: %f" % (time.time()-startTime))
    
    log("Gratingtimer stopped.")
    log("Viewtimer stopped.")
    log("Camera/file released.")
    
    #grating.stopGrating()
    gratingtimer.stop()
    viewtimer.stop()
    cap.release()
    
    
    #makedirs(SAVING_PATH+preface+LAST_FISH_ID)
    #log("New folder created: %s%s" % (preface,LAST_FISH_ID))
    
    logText = t2.toPlainText()

    with open(SAVING_PATH+"/"+"%s_log.txt" % expStart,"w") as f:
        f.write(logText)
    
    cv2.imwrite(SAVING_PATH+"/"+"%s_image.png"%expStart, the_fish)
    
    np.save(SAVING_PATH+"/"+"%s_data.npy" % expStart, np.array(savingPrivateRyan))
    
    
    import pandas as pd
    
    df = pd.DataFrame(np.array(savingPrivateRyan))
    df.columns = ('time [ms]', 'tail sum', 'vigor', 'grating speed', 'swimming', 'condition speed [mm/s]', 'applied gain', 'trial')
    df.to_csv(SAVING_PATH+"/"+"%s_data.csv" % expStart, index=False)
    
    
    
    #np.save(SAVING_PATH+preface+LAST_FISH_ID+"/"+"%s_grating.npy" % expStart, grating.getGrating())
    log("Data saved as %s_data.npy" % expStart)
    
def log(text):
    global t2
    t2.moveCursor(QtGui.QTextCursor.End)
    t2.insertPlainText("%s\n" % text)
    
    
def fishIsAligned ():
    global grating
    
    grating.alignToFish()
    
    log("Experiment can start")
    
def setGain ():
    global gain, GainBox
    
    gain = int(GainBox.text())
    
    log("Gain was set to %d" % gain)
    
def pauseResume ():
    global viewtimer, gratingtimer, isExperimentRunning
    
    if isExperimentRunning:
        viewtimer.stop()
        gratingtimer.stop()
        isExperimentRunning = False
        log("%s: Experiment paused." % str(datetime.now()))
        
    else:
        viewtimer.start(0)
        gratingtimer.start(10)
        isExperimentRunning = True
        log("%s: Experiment paused." % str(datetime.now()))
        
    
def rollMe (input, new_val):
    tmp = input[1:]
    tmp.append(new_val)
    
    return tmp
    
# Trace the tail using image
def tail_trace(img):
    #img = imgQ.get()

    global im, tail_sum_frames, THE_MODULO, vigor, rolling_buffer, borders, width, o, qim, SHOW_CIRCLES
    
    num_points = 10
    
    
    
    # X/Y position on tail base
    x = borders['tailbase'][0] #-width/num_points
    y = borders['tailbase'][1] #-height/num_points
    

    
    # Create an arc of 180 deg
    lin = np.linspace(np.pi/3,3/3*np.pi,20)

    # Initiate tail_points
    tail_points = [(x,y)]
    tail_sum = 0

    img_filt = np.zeros(img.shape)
    img_filt = cv2.boxFilter(img, -1, (7,7), img_filt)
    #img_filt = img
   # im.setImage(img_filt)
   
    if o == 3:
        print(img_filt.shape)

    #plt.figure()

    # Iterate 9 times.
    for j in range(num_points):
        # Find the x and y values of the arc
        xs = x+width/num_points*np.sin(lin)
        ys = y+width/num_points*np.cos(lin)
                
        
        # Convert them to integer, because of definite pixels
        xs, ys = xs.astype(int), ys.astype(int)
        
        
        #if o == 2:
        #    log("xs: %d, ys: %d" % (xs[0],ys[0]))
        #print img.shape
        
        # Remove points out of the scene
        xs = xs[xs<img.shape[1]-1]
        ys = ys[ys<img.shape[0]-1]
        
        if 1:
            for a in zip(xs, ys):
                cv2.circle(img,a,1,(255,0,0),1)
        
        if len(xs) != len(ys):
            return False
        
        # Find the minimum
        #plot3.plot(img_filt[ys,xs])
     
        ident = np.where(img_filt[ys,xs]==min(img_filt[ys,xs]))[0][0]
        
        #plot3.plot(img_filt[ys,xs])
            
        # The minimum is the starting point of the next arc
        x = xs[ident]
        y = ys[ident]
        
        # Add the angle to a total tail sum!
        tail_sum += np.cos(lin[ident])
        
        # Create an 180 deg angle depending on the previous one
        lin = np.linspace(lin[ident]-np.pi/3,lin[ident]+np.pi/3,20) 
     
        # Add point to list
        tail_points.append((x,y))
            
    # draw the circles onto the fish's tail
    for i in tail_points:
        cv2.circle(img,i,2,(0,0,0),1)
        
    if o % THE_MODULO*2 == 0:    
        #im.setImage(img)
        resized_img = 255-img#[400:]
        #resized_img = img
        qim_tmp = QtGui.QImage(resized_img, resized_img.shape[1], resized_img.shape[0], QtGui.QImage.Format_Indexed8)
        qim.setPixmap(QtGui.QPixmap.fromImage(qim_tmp))
        
    
    
    tail_sum_frames = rollMe(tail_sum_frames, tail_sum)
    #tail_sum_frames.append(tail_sum)
    
    #tail_sum_frames = np.roll(tail_sum_frames, -1)
    #tail_sum_frames[-1] = tail_sum
    
    # preset empty rolling buffer with tail_sum
    # to overcome initial overshoot
    #if not rolling_buffer.all():
    #    rolling_buffer[:] = tail_sum
    
    if rolling_buffer == None:
        rolling_buffer = [tail_sum]*12
    
    # roll the buffer and add the last element
    #rolling_buffer = np.roll(rolling_buffer,-1)
    #rolling_buffer[-1] = tail_sum
    rolling_buffer = rollMe(rolling_buffer, tail_sum)
    vigor = rollMe(vigor, np.std(rolling_buffer))
    #vigor.append(np.std(rolling_buffer))
    
    #vigor = np.roll(vigor, -1)
    #vigor[-1] = np.std(rolling_buffer)
    

#app = QtGui.QApplication([])
## Always start by initializing Qt (only once per application)
#if not app:
app = QtGui.QApplication([])


# Preset file
fn = "C:/Users/anki/OneDrive/Videos/2_compressed_200fps_8bitgrey.avi"
gain = 20 # Preset gain ^= 1





# where's the base, where's the tip?
#borders = {'tailbase': [430, 237], 'tailtip': [70, 255]}


# get tail length == width and "height"
#height = borders['tailbase'][1]-borders['tailtip'][1]
#width  = borders['tailbase'][0]-borders['tailtip'][0]

height = None
width  = None

#################################
#################################
#################################
#framei = np.zeros((100,))
#tail_sum_frames = np.zeros((400,))
#vigor = np.zeros((400,))
#rolling_buffer = np.zeros((25,))

framei = [0]*100
#tail_sum_frames = []
tail_sum_frames = [0]*400
#vigor = []
vigor = [0]*400
data3 = [0]*400
gain_course = [1]*400
rolling_buffer = None


o = 0    
    
## Define a top-level widget to hold everything
w = QtGui.QWidget()


            
            
###################
## SELECT TAIL ####
###################

class SelectTail(QtGui.QWidget):

    def __init__(self, img, what):
        super(SelectTail, self).__init__()
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.pos = []
        self.initUI(img, what)

    def mousePressEvent(self, QMouseEvent):
        img_tmp = self.img+1
        pos = QMouseEvent.x(), QMouseEvent.y()
        self.pos = pos
        
        cv2.circle(img_tmp,pos,5,(255,0,0),1)
        QI = QtGui.QImage(img_tmp.data, img_tmp.shape[1],img_tmp.shape[0], QtGui.QImage.Format_Indexed8)
        
        self.l.setPixmap(QtGui.QPixmap.fromImage(QI))
        self.update()    
        
        borders[self.what] = pos
        log('Position "%s" was set to (%d,%d)!' % (self.what, pos[0], pos[1]))

    def initUI(self,img, what):                 
        
        self.img = img

        
        QI = QtGui.QImage(img.data, img.shape[1],img.shape[0], QtGui.QImage.Format_Indexed8)
        
        self.l = QtGui.QLabel(self)
        self.l.setPixmap(QtGui.QPixmap.fromImage(QI))
        self.what = what

        self.setGeometry(0, 0, img.shape[1],img.shape[0])
        self.setWindowTitle('Select the tail %s' % what)    
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)
        #self.connect("clicked", self.test)
        self.show()
    def visible(self):
        return self.isVisible()

data1 = data2 = timestamp = [0]*400

## Create some widgets to be placed inside
statusBar = QtGui.QStatusBar() # Status bar
t2 = QtGui.QTextEdit() # Info field
t2.setReadOnly(True) # Only readonly

listw = QtGui.QListWidget()
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
plot1, curve1 = uplot([-4, 4])

plot1.setLabels(left="angle sum",bottom="time")

plot2, curve2 = uplot([0,2.5])

plot2.setLabels(left="vigor",bottom="time")

plot3, curve3 = uplot([-100, 20])
plot3.setLabels(left="speed",bottom="time")

#### GAIN INDICATOR #####
plot4, curve4 = uplot([-.2, 1.2])
plot4.setLabels(left="gain",bottom="time")



#####################################
### OLD IMG #########################
#imwidget = pg.GraphicsLayoutWidget()
#view = imwidget.addViewBox()
#view.setAspectLocked(True)
#im = pg.ImageItem(border='w')
#view.addItem(im)

qimW = QtGui.QWidget()
qimW.setMinimumSize(400,450)
qim = QtGui.QLabel(qimW)
qim.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
qim.setAlignment(QtCore.Qt.AlignCenter)
data = np.zeros((350,400))
qim_tmp = QtGui.QImage(data, data.shape[1], data.shape[0], QtGui.QImage.Format_Indexed8)
qim.setPixmap(QtGui.QPixmap.fromImage(qim_tmp))



#view.setRange(QtCore.QRectF(0, 0, 200, 200))

MyButton = QtGui.QPushButton("           Fish is aligned.           ")
MyButton.clicked.connect(fishIsAligned)


BenjaminButton = QtGui.QPushButton("Save data set")
BenjaminButton.clicked.connect(stopAndSave) 

PauseButton = QtGui.QPushButton("Pause/Resume Experiment")
PauseButton.clicked.connect(pauseResume) 

showCirclesB = QtGui.QPushButton("Show Circles")
showCirclesB.clicked.connect(showCircles) 

GainBox = QtGui.QLineEdit()
GainBox.setText(str(gain))
GainBox.textChanged.connect(setGain)


## Create a grid layout to manage the widgets size and position
layout = QtGui.QGridLayout()
w.setLayout(layout)
layout.setColumnStretch(0,1)


## Add widgets to the layout in their proper positions
layout.addWidget(plot1, 0, 0, 1, 2)  # plot goes on right side, spanning 3 rows
layout.addWidget(plot2, 1, 0, 1, 1)  # plot goes on right side, spanning 3 rows
layout.addWidget(plot3, 1, 1, 1, 1)  # plot goes on right side, spanning 3 rows
layout.addWidget(plot4, 2, 0, 1, 2)  # plot goes on right side, spanning 3 rows


layout.addWidget(BenjaminButton, 3, 0, 1, 1)
layout.addWidget(MyButton, 3, 1, 1, 1)
layout.addWidget(PauseButton, 3, 2, 1, 1)
layout.addWidget(GainBox,3,3,1,1)

#layout.addWidget(showCirclesB,4,0,4,1)


#layout.addWidget(imwidget,0, 2, 2, 2)
layout.addWidget(qimW,0, 2, 2, 2)
layout.addWidget(t2, 2, 2, 1, 2)



layout.addWidget(statusBar,4,0,1,4)
## Display the widget as a new window
w.showMaximized()
#w.show()
grating = Grating(px_per_mm=2.95)

grating.setGratingSpeed(Conditions[0])
grating.show()
# Select a Fgratingile
#fn = QtGui.QFileDialog.getOpenFileName()[0]
#cap = cv2.VideoCapture(fn) # Open video with openCV
cap = cv2.VideoCapture(device)


#imgQ = Queue()
#aP = Process(tail_trace, args=(imgQ, ))
#aP.start()

cap.set(15,EXPOSURE_TIME)
time.sleep(1)
_, f = cap.read()

the_fish = f+1


#f = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)

#cv2.imwrite(SAVING_PATH+"%s_image.png"%expStart, f)
cap.set(15,EXPOSURE_TIME)
cap.set(415,False)
log("Exposure time: %d" % EXPOSURE_TIME)
time.sleep(1)
# Create the loop
startTime = last_upd = time.time()
grating_incr = time.time()



def select_the_tail ():
    pass
    
borders = {'tailbase': [], 'tailtip': []}

tip  = SelectTail(cv2.resize(f, None, fx=0.5, fy=0.5), "tailtip")
#app.exec_()
base = SelectTail(cv2.resize(f, None, fx=0.5, fy=0.5), "tailbase")
#app.exec_()

log("%s: Trial %d" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), CurTrial))
        

# get tail length == width and "height"
#height = borders['tailbase'][1]-borders['tailtip'][1]
#width  = borders['tailbase'][0]-borders['tailtip'][0]


viewtimer = QtCore.QTimer()
viewtimer.timeout.connect(updateview)
viewtimer.start(0)

gratingtimer = QtCore.QTimer()
gratingtimer.timeout.connect(grating.show)


if SAVING_PATH is None:
    SAVING_PATH = QtGui.QFileDialog.getExistingDirectory(directory=JUMP_TO)
        
SP = "\\".join(SAVING_PATH.split("\\")[:-1])
        
m = Metadata(SP, SAVING_PATH+"/%s_metadata"%expStart)




## Start the Qt event loop
app.exec_()