# CV-Extractors


## Overview

All extractors here use **OpenCV** to extract information from images. You will need Python and OpenCV to be installed in your system.

These extractors were developed and tested on Mac 64-bits. OpenCV pre-trainned classifiers are expected to be stored at /opt/local/share/OpenCV/haarcascades.

To use this extractor you will need pyclowder installed. You can either install it, or you can create a link to the pyclowder repository. Assuming that the pyclowder repository is cloned in the same folder as this repository you can execute the following code `ln -s $(cd "../../pyclowder/pyclowder" && pwd -P) pyclowder`.

In config.py you will need to set the URL to point to rabbitmq (https://www.rabbitmq.com/uri-spec.html). For example to connect to rabbitmq running on the localhost with default parameters you can use the following URL: amqp://guest:guest@localhost:5672/%2f

## Input
An image file to extract information from. Input format must be supported by OpenCV.
  
Formats supported by OpenCV (imread) and possible necessary codecs are listed on the OpenCV documentation [here](http://docs.opencv.org/modules/highgui/doc/reading_and_writing_images_and_video.html?#imread).

## Output
Outputs vary depending on the extractor. Each also adds metadata to
the file.

* face: detects faces on images and creates sections (and their previews which are images containing only the detected faces) and tags for the detected faces.
* profile: detects profile of human faces on images and creates sections, the section previews (which are images containing only the detected profiles), and tags for the detected profiles.
* eyes: detect eyes on images and creates sections, previews for the sections (images containing the detected eyes) and tags for the detected eyes.
* closeup: detects whether an image is a closeup on a person and tags
the image accordingly.

## Sample input and output files in this directory
* face: sample input file: Amitabha.jpg, sample output file: Amitabha.jpg.sample-output.

## Build a docker image
      docker build -t ncsa/clowder-opencv-faces:jsonld .

## Test the docker container image:

      docker run --name=opencv-faces-1 -d --restart=always -e 'RABBITMQ_URI=amqp://user1:pass1@rabbitmq.ncsa.illinois.edu:5672/clowder-dev' -e 'RABBITMQ_EXCHANGE=clowder' -e 'TZ=/usr/share/zoneinfo/US/Central' -e 'REGISTRATION_ENDPOINTS=http://dts-dev.ncsa.illinois.edu:9000/api/extractors?key=key1' ncsa/clowder-opencv-faces:jsonld

    Then upload files to Clowder to test the extractor. You might need
    to upload multiple times for a file to go to this extractor
    instance if there are multiple instances for the same queue.
    Change the file, Clowder URL, key in the following to your values.

      curl -F "File=@Amitabha.jpg" 'http://dts-dev.ncsa.illinois.edu:9000/api/extractions/upload_file?key=key1'

## To view the log files (similar to "tail -f")

      docker logs -f opencv-faces-1

  Setting the timezone variable (TZ) above is optional. It can help
  understand better the time shown in the log file. By default
  a container uses UTC.
