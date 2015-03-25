# CV-Extractors


## Overview

All extractors here use **OpenCV** to extract information from images. You will need Python and OpenCV to be installed in your system.

These extractors were developed and tested on Mac 64-bits. OpenCV pre-trainned classifiers are expected to be stored at /opt/local/share/OpenCV/haarcascades.

To use this extractor you will need pymedici installed. You can either install it, or you can create a link to the pymedici repository. Assuming that the pymedici repository is cloned in the same folder as this repository you can execute the following code `ln -s $(cd "../../pyMedici/pymedici" && pwd -P) pymedici`.

In config.py you will need to set the URL to point to rabbitmq (https://www.rabbitmq.com/uri-spec.html). For example to connect to rabbitmq running on the localhost with default parameters you can use the following URL: amqp://guest:guest@localhost:5672/%2f

## Input
An image file to extract information from. Input format must be supported by OpenCV.  
  
Formats supported by OpenCV (imread) and possible necessary codecs are listed on the OpenCV documentation [here](http://docs.opencv.org/modules/highgui/doc/reading_and_writing_images_and_video.html?#imread).

## Output
Outputs vary depending on the extractor.

* face: detects faces on images and creates sections (and their previews which are images containing only the detected faces) and tags for the detected faces.
* profile: detects profile of human faces on images and creates sections, the section previews (which are images containing only the detected profiles), and tags for the detected profiles.
* eyes: detect eyes on images and creates sections, previews for the sections (images containing the detected eyes) and tags for the detected eyes.
* closeup: detects whether an image is a closeup on a person and tags the image accordingly.