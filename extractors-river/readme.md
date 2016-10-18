# River Extractor


## Overview

Tries to clean up lines from old maps and leave only the rivers annotated in the maps.

The extractor uses **OpenCV** (python), **convert** (from imagemagick), and **Gdal** (gdal-bin and python-gdal) to process the images. You will need all of these to be installed in your system.

To use this extractor you will need pymedici installed. You can either install it, or you can create a link to the pymedici repository. Assuming that the pymedici repository is cloned in the same folder as this repository you can execute the following code `ln -s $(cd "../../pyMedici/pymedici" && pwd -P) pymedici`.

In config.py you will need to set the URL to point to rabbitmq (https://www.rabbitmq.com/uri-spec.html). For example to connect to rabbitmq running on the localhost with default parameters you can use the following URL: amqp://guest:guest@localhost:5672/%2f

This extractor was tested on a 64-bit Mac OS using Python 2.7.5.

## Input
A tif with geolocation  
  
## Output
A tif with geolocation contaning a much cleaner image of the map

