# CV-Extractors


## Overview

All extractors here use **OpenCV** to extract information from images. You will need Python and OpenCV to be installed in your system.


## Input
An image file to extract information from. Input format must be supported by OpenCV.  
  
Formats supported by OpenCV (imread) and possible necessary codecs are listed on the OpenCV documentation [here](http://docs.opencv.org/modules/highgui/doc/reading_and_writing_images_and_video.html?#imread).

## Output
Outputs vary depending on the extractor.

* face: detects faces on images and creates sections (and their previews which are images containing only the detected faces) and tags for the detected faces.
* profile: detects profile of human faces on images and creates sections, the section previews (which are images containing only the detected profiles), and tags for the detected profiles.
* eyes: detect eyes on images and creates sections, previews for the sections (images containing the detected eyes) and tags for the detected eyes.
* closeup: detects whether an image is a closeup on a person and tags the image accordingly.