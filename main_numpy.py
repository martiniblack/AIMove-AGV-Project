import cv2
import glob
import json
import os
import re
import numpy as np
import matplotlib.pyplot as plt
import pyrealsense2 as rs
# import pandas as pd
from time import time
import warnings
warnings.filterwarnings("ignore")

# Configure depth and color streams
pipeline = rs.pipeline()
config = rs.config()
max_image_X = 640
max_image_Y = 480
config.enable_stream(rs.stream.depth, max_image_X, max_image_Y, rs.format.z16, 15)
config.enable_stream(rs.stream.color, max_image_X, max_image_Y, rs.format.bgr8, 15)

# Start streaming
pipeline.start(config)
align_to = rs.stream.color
align = rs.align(align_to)

from initialize_OP import *
# Starting OpenPose
params['number_people_max'] = 1
opWrapper = op.WrapperPython()
opWrapper.configure(params)
opWrapper.start()

# Initialize numpy matrix of result
data_window = np.zeros((0,7,4))

# Number of time lenght (defined pas fps)
max_frame_iter = 100

plt.ion()
fig = plt.figure()

try:
    # Initialize variable iteration of frames
    frame_iter = 0

    while True:

        start_time = time()

        # Wait for a coherent pair of frames: depth and color
        frames = pipeline.wait_for_frames()
        aligned_frames = align.process(frames)

        aligned_depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()

        if not aligned_depth_frame or not color_frame:
            continue

        # Get frame number
        n_frame = frames.get_frame_number()

        # Convert images to numpy arrays
        depth_image = np.asanyarray(aligned_depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        plt.clf()
        plt.subplot(2, 1, 1)
        plt.imshow(color_image)
        plt.subplot(2, 1, 2)
        plt.imshow(depth_image)

        # Convert depth_image to normalized depth information
        depthImg = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
        img_depth = cv2.cvtColor(depthImg, cv2.COLOR_BGR2GRAY)
        img_depth = img_depth / 255

        # Process and display images
        X = np.empty((0))
        Y = np.empty((0))
        Depth = np.empty((0))
        Probability = np.empty((0))

        datum = op.Datum()
        datum.cvInputData = color_image
        opWrapper.emplaceAndPop([datum])
        opData = datum.poseKeypoints
        #print('datum.poseKeypoints.shape :', datum.poseKeypoints.shape, '\n')

        X = np.empty((0))
        Y = np.empty((0))
        Depth = np.empty((0))
        Probability = np.empty((0))

        data_joint = np.zeros((0,4))
        for joint in range(1, 8):
            x = opData[0][joint][0].item()
            y = opData[0][joint][1].item()
            probability = opData[0][joint][2].item()
            depth = img_depth[min(color_image.shape[0]-1, round(y)), min(color_image.shape[1]-1, round(x))]

            X = np.append(X, min(img_depth.shape[1] - 1, round(x)))
            Y = np.append(Y, min(img_depth.shape[0] - 1, round(y)))
            Probability = np.append(Probability, probability)
            Depth = np.append(Depth, depth)

            data_keypoint = np.array([x/max_image_X, y/max_image_Y, probability, depth])
            data_joint = np.vstack((data_joint, data_keypoint))

        data_window = np.vstack((data_window, data_joint.reshape(1, 7, 4)))

        plt.subplot(2, 1, 1)
        plt.scatter(X, Y, c='white')
        for i in range(0,7):
            plt.text(X[i], Y[i], "%.02f" % Probability[i], fontdict=dict(color='white', size='15'), bbox=dict(fill=False, edgecolor='red', linewidth=1))

        plt.subplot(2, 1, 2)
        plt.scatter(X, Y, c='white')
        for i in range(0,7):
            plt.text(X[i], Y[i], "%.02f" % Depth[i], fontdict=dict(color='black', size='15'), bbox=dict(fill=False, edgecolor='red', linewidth=1))

        plt.waitforbuttonpress(0.0001)
        plt.show()

        if not args[0].no_display:
             cv2.imshow("OpenPose 1.5.0 - Tutorial Python API", datum.cvOutputData)
             key = cv2.waitKey(15)
             if key == 27: break

        frame_iter = frame_iter + 1
        print('frame_iter :', frame_iter, '\tn_frame :', n_frame)

        if frame_iter == max_frame_iter:
            # Create DataFrame of keypoints
            print('data window shape:',data_window.shape)
            end_time = time()
            run_time = end_time - start_time
            print('run time', run_time)

            # Update variable iteration of frames
            frame_iter = max_frame_iter - 1
            # Delete first keypoints (first frame of the dataframe)
            data_window = data_window[1:,:,:]

        print(data_window)

        depth_median = np.median(data_window[:, :, 3], axis=0)

finally:
    # Stop streaming
     pipeline.stop()