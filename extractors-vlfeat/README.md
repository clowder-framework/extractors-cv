# Basic Caltech 101 category extractor

This extractor uses **Matlab** and **VLFeat** to classify images based on the Caltech 101 object categories. It was tested on a 64-bit Mac OS using Python 2.7.5, VLFeat 0.9.18, and Matlab R2013a.

To use this extractor you will need pymedici installed. You can either install it, or you can create a link to the pymedici repository. Assuming that the pymedici repository is cloned in the same folder as this repository you can execute the following code `ln -s $(cd "../../pyMedici/pymedici" && pwd -P) pymedici`.

In config.py you will need to set the URL to point to rabbitmq (https://www.rabbitmq.com/uri-spec.html). For example to connect to rabbitmq running on the localhost with default parameters you can use the following URL: amqp://guest:guest@localhost:5672/%2f

Please, read the setup section carefully before proceeding.

## Docker Build

To build this docker container use

```
docker build -t clowder/extractors-caltech101 .
```

This extractor assumes you will have mounted a completed matlab install at /matlab in the contiainer. You can install matlab on a ubuntu 64 bit machine and copy the resulting /usr/local/MATLAB/&lt;release&gt; folder.

To run the extractor use:

```
docker run --link rabbitmq:rabbitmq --volume ${PWD}/matlab:/matlab clowder/extractors-caltech101
```

## Overview
Use VLFeat to associate a category from the Caltech 101 benchmark with an image.

## Input
An image file.

## Output
The detected category and the score yielded by the classifier associated with the original file. 

## Setup
### VLFeat
VLFeat is available to download at [http://www.vlfeat.org](http://www.vlfeat.org) as a compressed file. Once the file is decompressed, it will create a folder called *vlfeat-0.X.XX* depending on the version downloaded. 

**Important:** This folder must be renamed as *vlfeat* and moved to the folder containing the extractor code. For example, if the extractor code files are located at "/.../extractors/caltech101", then the path to the VLFeat folder should be "/.../extractors/caltech101/vlfeat".

### Matlab
Matlab must be installed in your system and typing *matlab* in your terminal should open Matlab (i.e. Matlab must be in your PATH).

**Important:** the file *baseline-model.mat* must be moved to the folder "/.../vlfeat/apps/data/". If this folder does not exist, it must be created.

## Advanced settings
This extractor uses a simple model to classify the input image. 
The model provided here was trained using VLFeat's *phow_caltech101* function with the *tiny* setting turned off and the Caltech 101 images. However, not only the classifier can be retrained to get better results, but can also be adapted to your own categories and sample images.

More information about how to train the classifier and details about the entire process can be found at [VLFeat's applications](http://www.vlfeat.org/applications/apps.html) website under *Basic Recognition* and *Advanced encodings for recognition*.
