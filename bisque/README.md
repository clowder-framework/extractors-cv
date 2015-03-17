# Bisque extractors

These metadata and histogram extractors uses [Bisque](http://www.bioimage.ucsb.edu) to extract metadata and the histogram of the input image.
In order to use these extractors, you must have access to an instance of Bisque. The extractor is by default set to connect to [UCSB's public Bisque instance](http://bisque.ece.ucsb.edu/) and you will need to register at their website if you choose to use this Bisque instance. You can change this setting so that the extractors connect to your prefered instance of Bisque.

**Important**: These extractors use an external service and with such come some risks concerning your privacy. Files are uploaded to and deleted from Bisque by the extractors. We cannot guarantee that the files are properly secured and deleted from the Bisque instance server. You should read about your Bisque server privacy and security measures before proceeding.

In order for the extractor to work, your system needs to have installed **Python** and the following Python packages/modules: [**requests**](https://pypi.python.org/pypi/requests/2.3.0), [**pika**](https://pypi.python.org/pypi/pika).

**Important**: Your username/passwords must be entered in the Python config files (config.py). To do so, search for and change bisqueUser='' and bisquePassword='' to your info, for example bisqueUser='myusername' and bisquePassword='mypassword'.

To use this extractor you will need pymedici installed. You can either install it, or you can create a link to the pymedici repository. Assuming that the pymedici repository is cloned in the same folder as this repository you can execute the following code `ln -s $(cd "../../pyMedici/pymedici" && pwd -P) pymedici`.

In config.py you will need to set the URL to point to rabbitmq (https://www.rabbitmq.com/uri-spec.html). For example to connect to rabbitmq running on the localhost with default parameters you can use the following URL: amqp://guest:guest@localhost:5672/%2f

This extractor was tested on a 64-bit Mac OS using Python 2.7.5.

## Overview

The extractors use Bisque to extract an image's metadata and histogram. 

## Input
An image file.

## Output
The image's histogram or metadata (depending on the extractor).

        