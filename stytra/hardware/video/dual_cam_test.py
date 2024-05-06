from stytra.hardware.video.cameras import SpinnakerCamera
from stytra.hardware.video.cameras import XimeaCamera
import numpy as np
from time import sleep
import matplotlib.pyplot as plt


spin_cam = SpinnakerCamera()
xi_cam = XimeaCamera()
xi_cam_1 = XimeaCamera()

if __name__ == '__main__':
    spin_cam.open_camera()
    xi_cam.open_camera('23755650')
    xi_cam_1.open_camera('46054250')
    print ('d')
    for i in range(10):
        img = spin_cam.read()
        img_xi = xi_cam.read()
        img_xi_1 = xi_cam_1.read()

    sleep(0.2)
    spin_cam.release()
    xi_cam.release()
    xi_cam_1.release()
    print('done')

    print (img_xi.shape)
    plt.figure()
    plt.title('ximea')
    plt.imshow(img_xi)
    plt.show()

    print (img_xi_1.shape)
    plt.figure()
    plt.title('ximea1')
    plt.imshow(img_xi_1)
    plt.show()

    print(img.shape)
    plt.figure()
    plt.title("spinnaker")
    plt.imshow(img)
    plt.show()

