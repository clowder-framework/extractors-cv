# Simple OCR extractor

This extractor uses **Tesseract**. Information on Tesseract and how to install it can be found at the [Tesseract's project page](http://code.google.com/p/tesseract-ocr/).

This extractor uses pyClowder. Information on pyClowder can be found [here](https://github.com/clowder-framework/pyclowder).

This extractor depends on RabbitMQ. You will need to set the URL to point to RabbitMQ (https://www.rabbitmq.com/uri-spec.html). For example, to connect to RabbitMQ running on the localhost with default parameters you can use the following URL: amqp://guest:guest@localhost:5672/%2f
 
## Overview

Performs simple OCR on an image and associates the resulting text with it. The text is not supposed to be a perfect transcription, but a way to associate words with an image so to make images more searchable.

## Input
An image file in a format supported by Tesseract.

## Output
OCR text extracted from the input associated with the original file.

## Sample input and output files
A sample input file "browndog.png" and a sample output file "browndog.png.sample-output" are available in this directory.

## Test locally with Clowder
1. In extractors-cv/extractors-tesseract/ folder run: 
      
      ```docker build -t clowder/ocr:test .```

2. In the tests subdirectory, run: 

      ```docker-compose -f docker-compose.yml -f docker-compose.extractors.yml up -d```

3. Initialize Clowder: 

      ```docker run -ti --rm --network tests_clowder clowder/mongo-init```

4. Enter email, first name, last name password, and admin: true when prompted.
5. Navigate to localhost:9001 and login with credentials you created in step 4.
6. Create a test space and dataset. Then click 'Select Files' and upload tests/browndog.png.
7. Click on file and type submit for extraction.
8. It may take a few minutes for you to be able to see the extractors available within Clowder
9. Eventually you should see ocr in the list and click submit.
10. Navigate back to file and click on metadata.
11. You should see the ocr_text metadata present.

  Setting the timezone variable (TZ) above is optional. It can help
  understand better the time shown in the log file. By default
  a container uses UTC.
