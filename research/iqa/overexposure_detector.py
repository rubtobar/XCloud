# class wrapper for image overexposure detection
import cv2
import imutils
import numpy as np
from imutils import contours
from skimage import measure
from sklearn.metrics import confusion_matrix, precision_score, recall_score, accuracy_score


class OverExposureDetector:
    def __init__(self, show_result=True, large_blob_threshold=500, light_region_radius_min=60):
        self.show_result = show_result
        self.large_blob_threshold = large_blob_threshold
        self.light_region_radius_min = light_region_radius_min

    def cal_light_region_num(self, image):
        if isinstance(image, str):
            image = cv2.imread(image)
            image = cv2.resize(image, (400, 600))

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)

        # threshold the image to reveal light regions in the blurred image
        thresh = cv2.threshold(blurred, 235, 255, cv2.THRESH_BINARY)[1]

        # perform a series of erosions and dilations to remove
        # any small blobs of noise from the thresholded image
        thresh = cv2.erode(thresh, None, iterations=2)
        thresh = cv2.dilate(thresh, None, iterations=4)

        # perform a connected component analysis on the thresholded
        # image, then initialize a mask to store only the "large" components
        labels = measure.label(thresh, neighbors=8, background=0)
        mask = np.zeros(thresh.shape, dtype="uint8")

        for label in np.unique(labels):
            # if this is the background label, ignore it
            if label == 0:
                continue

            # otherwise, construct the label mask and count the
            # number of pixels
            label_mask = np.zeros(thresh.shape, dtype="uint8")
            label_mask[labels == label] = 255
            num_pixels = cv2.countNonZero(label_mask)

            # if the number of pixels in the component is sufficiently
            # large, then add it to our mask of "large blobs"
            if num_pixels > self.large_blob_threshold:
                mask = cv2.add(mask, label_mask)

        # find the contours in the mask, then sort them from left to right
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        if len(cnts) == 0:
            return {'light_region_num': len(cnts), 'overexposure': False}

        cnts = contours.sort_contours(cnts)[0]
        light_region_num = 0

        for (i, c) in enumerate(cnts):
            # draw the bright spot on the image
            _, radius = cv2.minEnclosingCircle(c)
            # print(radius)
            if radius >= self.light_region_radius_min:
                light_region_num += 1

        if self.show_result:
            for (i, c) in enumerate(cnts):
                # draw the bright spot on the image
                (x, y, w, h) = cv2.boundingRect(c)
                ((cX, cY), radius) = cv2.minEnclosingCircle(c)
                if radius >= self.light_region_radius_min:
                    cv2.circle(image, (int(cX), int(cY)), int(radius),
                            (0, 0, 255), 3)
                    cv2.putText(image, "#{}".format(i + 1), (x, y - 15),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)

            cv2.imshow("Image", image)
            cv2.waitKey()

        return {'light_region_num': light_region_num, 'overexposure': light_region_num > 0}


if __name__ == '__main__':
    reflection_detector = OverExposureDetector(False)
    import os
    import time

    tik = time.time()
    preds = []
    gts = []

    normal_img_dir = './normal'
    for _ in os.listdir(normal_img_dir):
        res = reflection_detector.cal_light_region_num(os.path.join(normal_img_dir, _))
        print(res)
        if not res['overexposure']:
            preds.append(0)
        else:
            preds.append(1)

        gts.append(0)

    exposure_img_dir = './exposure'
    for _ in os.listdir(exposure_img_dir):
        res = reflection_detector.cal_light_region_num(os.path.join(exposure_img_dir, _))
        print(res)
        if res['overexposure']:
            preds.append(0)
        else:
            preds.append(1)

        gts.append(1)

    tok = time.time()
    print('FPS={}'.format((len(os.listdir(exposure_img_dir)) + len(os.listdir(normal_img_dir))) / (tok - tik)))

    print(confusion_matrix(gts, preds))
    print('Precision = %f' % precision_score(gts, preds))
    print('Recall = %f' % recall_score(gts, preds))
    print('Accuracy = %f' % accuracy_score(gts, preds))
