# Simple OCR extractor

This extractor uses **Tesseract**, which needs to be installed in your system. Information on Tesseract and how to install it can be found at the [Tesseract's project page](http://code.google.com/p/tesseract-ocr/).

This extractor was tested on a 64-bit Mac OS using Python 2.7.5.

To use this extractor you will need pymedici installed. You can either install it, or you can create a link to the pymedici repository. Assuming that the pymedici repository is cloned in the same folder as this repository you can execute the following code `ln -s $(cd "../../pyMedici/pymedici" && pwd -P) pymedici`.

In config.py you will need to set the URL to point to rabbitmq (https://www.rabbitmq.com/uri-spec.html). For example to connect to rabbitmq running on the localhost with default parameters you can use the following URL: amqp://guest:guest@localhost:5672/%2f
 
## Overview

Performs simple OCR on an image and associates the resulting text with it. The text is not supposed to be a perfect transcription, but a way to associate words with an image so to make images more searchable.

## Input
An image file in a format supported by Tesseract.

## Output
OCR text extracted from the input associated with the original file.


## Build a docker image

      `docker build -t clowder/ocr:0.1 .`

## Test the docker container image:

      `docker run --name=ocr1 -e 'RABBITMQ_URI="amqp://user1:password1@rabbitmq.ncsa.illinois.edu:5672/vhost1?heartbeat_interval=120"' -e 'RABBITMQ_EXCHANGE="exchange1"' -e 'TZ=/usr/share/zoneinfo/US/Central' clowder/ocr:0.1`

## To view the log files (similar to "tail -f")

      `docker logs -f ocr1`

  Setting the timezone variable above is optional. It can help
  understand better the time shown in the log file. By default
  a container uses UTC.
