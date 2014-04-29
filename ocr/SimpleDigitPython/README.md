# Single Python Handwritten Digit extractor

This extractor wraps a Python OpenCV sample application in order to identify the digit depicted in the image.
Both **Pyhton** and its **OpenCV** module need to be installed. To verify whether this module is installed in your system, type open a Python environment and type *import cv2* . If no error message is displayed, the module is installed in your system already. Otherwise, instructions on how to install OpenCV can be found in [http://docs.opencv.org](http://docs.opencv.org).

**Important:** This extractor call functions from [digits.py](https://github.com/Itseez/opencv/blob/master/samples/python2/digits.py) and [common.py](https://github.com/Itseez/opencv/blob/master/samples/python2/common.py) from the OpenCV sample repository. These need to be downloaded and added to the same folder as the extractor.

This extractor was tested on a 64-bit Mac OS using Python 2.7.5.

## Overview

Indentifies a single handwritten digit displayed in an image. The image should contain only the digit, which should cover most of the image (i.e., the image should contain no additional space other than the one necessary to display the digit).

The model used here was trained using an image aggregate of digit images from the [MNIST dataset](http://yann.lecun.com/exdb/mnist/). The training image can be found in the opencv sample application's [data folder](https://github.com/Itseez/opencv/blob/master/samples/python2/data/digits.png).

## Input
An image file.

## Output
The handwritten digit identified in the image associated with the original file.
