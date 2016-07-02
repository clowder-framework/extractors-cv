# Simple OCR extractor

This extractor uses **Tesseract**, which needs to be installed in your system. Information on Tesseract and how to install it can be found at the [Tesseract's project page](http://code.google.com/p/tesseract-ocr/).

This extractor was tested on a 64-bit Mac OS using Python 2.7.5.

To use this extractor you will need pyclowder installed. You can either install it, or you can create a link to the pyclowder repository. Assuming that the pyclowder repository is cloned in the same folder as this repository you can execute the following code `ln -s $(cd "../../pyclowder/pyclowder" && pwd -P) pyclowder`.

In config.py you will need to set the URL to point to rabbitmq (https://www.rabbitmq.com/uri-spec.html). For example to connect to rabbitmq running on the localhost with default parameters you can use the following URL: amqp://guest:guest@localhost:5672/%2f
 
## Overview

Performs simple OCR on an image and associates the resulting text with it. The text is not supposed to be a perfect transcription, but a way to associate words with an image so to make images more searchable.

## Input
An image file in a format supported by Tesseract.

## Output
OCR text extracted from the input associated with the original file.

## Sample input and output files
A sample input file "browndog.png" and a sample output file "browndog.png.sample-output" are available in this directory.

## Build a docker image
      docker build -t ncsa/clowder-ocr:jsonld .

## Test the docker container image:

      docker run --name=ocr1 -d --restart=always -e 'RABBITMQ_URI=amqp://user1:pass1@rabbitmq.ncsa.illinois.edu:5672/clowder-dev' -e 'RABBITMQ_EXCHANGE=clowder' -e 'TZ=/usr/share/zoneinfo/US/Central' -e 'REGISTRATION_ENDPOINTS=http://dts-dev.ncsa.illinois.edu:9000/api/extractors?key=key1' ncsa/clowder-ocr:jsonld

Then upload files to Clowder to test the extractor. You might need
to upload multiple times for a file to go to this extractor
instance if there are multiple instances for the same queue.
Change the file, Clowder URL, key in the following to your values.

      curl -F "File=@browndog.png" 'http://dts-dev.ncsa.illinois.edu:9000/api/extractions/upload_file?key=key1'

Then look at the logs in the container.

      docker logs -f ocr1

One of the uploaded files will be given to the extractor container
to process. Find a file id in the log, and open the following URL
in a browser window to verify that the metadata added by the OCR 
extractor is there. Again change the Clowder URL accordingly.

      http://dts-dev.ncsa.illinois.edu:9000/files/<file_id>

## To view the log files (similar to "tail -f")

      docker logs -f ocr1

  Setting the timezone variable (TZ) above is optional. It can help
  understand better the time shown in the log file. By default
  a container uses UTC.
