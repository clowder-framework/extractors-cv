# Pdf image extractor

This extractor uses **pdfimages**, from **poppler-utils**, which needs to be installed in your system. Information on pdfimages and poppler and how to install it can be found at the [Poppler project page](http://poppler.freedesktop.org). In Ubuntu, it can be installed using apt-get (`apt-get install poppler-utils`).

This extractor was tested on a 64-bit Mac OS using Python 2.7.5.

To use this extractor you will need pymedici installed. You can either install it, or you can create a link to the pymedici repository. Assuming that the pymedici repository is cloned in the same folder as this repository you can execute the following code `ln -s $(cd "../../pyMedici/pymedici" && pwd -P) pymedici`.

In config.py you will need to set the URL to point to rabbitmq (https://www.rabbitmq.com/uri-spec.html). For example to connect to rabbitmq running on the localhost with default parameters you can use the following URL: amqp://guest:guest@localhost:5672/%2f

You will also need to set the path to the pdfimages executable (pdfimagespath in the config file).
 
## Overview

Extracts images from pdf files.

## Input
A pdf file.

## Output
The images extracted from the input associated with the original file.

        