# Basic Caltech 101 category extractor

This extractor uses **Matlab** and **VLFeat** to classify images based on the Caltech 101 object categories. It was tested on a 64-bit Mac OS using Python 2.7.5, VLFeat 0.9.18, and Matlab R2013a.

## Installing and Running Extractor Outside of Docker
To install and run the python extractor do the following:

1. Setup a Python [virtual environment](https://virtualenv.pypa.io/)
2. Install PyClowder2: ```pip install git+https://opensource.ncsa.illinois.edu/stash/scm/cats/pyclowder2.git```
3. Start extractor: ```python caltech101extractor.py```

Please, read the setup section carefully before proceeding.

## Installing and Running Extractor Using Docker
### Build Docker Image

To build this docker container use

```
docker build -t clowder/extractors-vlfeat .
```
### Run Docker Container
This extractor assumes you will have mounted a completed matlab install at /matlab in the container. You can install matlab on a ubuntu 64 bit machine and copy the resulting /usr/local/MATLAB/&lt;release&gt; folder.

To run the extractor use:

```
docker run --rm -i -t --link extractorsvlfeat_rabbitmq_1:rabbitmq --volume ${PWD}/matlab:/matlab clowder/extractors-vlfeat
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
