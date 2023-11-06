from stytra.hardware.video.cameras import SpinnakerCamera
from stytra.hardware.video.cameras import XimeaCamera
import numpy as np
from time import sleep
import matplotlib.pyplot as plt


spin_cam = SpinnakerCamera()
xi_cam = XimeaCamera()

if __name__ == '__main__':
    spin_cam.open_camera()
    print ('d')
    for i in range(10):
        img = spin_cam.read()

    sleep(0.2)
    spin_cam.release()
    print ('done')

    xi_cam.open_camera()
    print('d')
    for i in range(10):
        img_xi = xi_cam.read()

    sleep(0.2)
    xi_cam.release()
    print('done')

    # print (img.shape)
    # plt.figure()
    # plt.imshow(img)
    # plt.show()
    #
    # print (img_xi.shape)
    # plt.figure()
    # plt.imshow(img_xi)
    # plt.show()

    test_arr = np.zeros((img_xi.shape[0], img_xi.shape[1] + img.shape[1]))
    print(test_arr.shape)
    test_arr[:img_xi.shape[0], :img_xi.shape[1]] = img_xi
    test_arr[:img.shape[0], img_xi.shape[1]:] = img

    plt.figure()
    plt.imshow(test_arr)
    plt.show()

