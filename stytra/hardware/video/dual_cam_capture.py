import cv2
import time
import os
import imutils
from stytra.hardware.video.cameras import SpinnakerCamera, XimeaCamera

def capture_synced_videos(output_folder1, output_folder2, duration):
    if not os.path.exists(output_folder1):
        os.makedirs(output_folder1)
    if not os.path.exists(output_folder2):
        os.makedirs(output_folder2)
    # xi_cam = XimeaCamera()
    # xi_cam.open_camera('46054250')
    # xi_cam.set("exposure", 30)
    # xi_cam.set("framerate", 30)
    spin_cam1 = SpinnakerCamera(1)
    spin_cam = SpinnakerCamera(0)
    spin_cam1.open_camera()
    spin_cam.open_camera()
    spin_cam.set("exposure", 10)
    spin_cam1.set("exposure", 10)
    spin_cam.set("framerate", 20)
    spin_cam1.set("framerate", 20)

    # Define the codec and create VideoWriter objects
    # fourcc = cv2.VideoWriter_fourcc(*'XVID')
    # shape = (1024, 1280)
    # out1 = cv2.VideoWriter("file1.avi", fourcc, 20.0, shape)
    # out2 = cv2.VideoWriter("file2.avi", fourcc, 20.0, shape)

    # Get the starting time
    start_time = time.time()
    frame_count = 0
    while True:
        # Capture frame-by-frame
        frame2 = spin_cam1.read()
        frame1 = spin_cam.read()
        frame1 = imutils.rotate(frame1, angle=90)

        # Write the frames to the respective output files
        # out1.write(frame1)
        # out2.write(frame2)
        filename1 = os.path.join(output_folder1, f"frame_{frame_count:04d}.jpg")
        filename2 = os.path.join(output_folder2, f"frame_{frame_count:04d}.jpg")
        cv2.imwrite(filename1, frame1)
        cv2.imwrite(filename2, frame2)
        # Display the resulting frames (optional)
        cv2.imshow('Camera 1', frame1)
        cv2.imshow('Camera 2', frame2)

        # Break the loop if the specified duration is reached
        if time.time() - start_time > duration:
            break

        # Press 'q' to exit the loop
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        frame_count += 1
    # Release everything if job is finished
    spin_cam.release()
    spin_cam1.release()
    # out1.release()
    # out2.release()
    cv2.destroyAllWindows()


output_folder1 = 'cam1'
output_folder2 = 'cam2'
duration = 60  # Duration in seconds
capture_synced_videos(output_folder1, output_folder2, duration)
