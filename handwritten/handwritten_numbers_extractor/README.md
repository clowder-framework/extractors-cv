# Handwritten Numbers extractor

This extractor uses **Matlab** and **mnist-sphog** to extract handwritten numbers from images. It was tested on a 32-bit Ubuntu OS using Python 2.7.3, and Matlab R2009a 32-bit (7.8.9.347).

Please, read the setup section carefully before proceeding.

## Overview
Use mnist-sphog to extract handwritten numbers from images.

## Input
An image file.

## Output
A list of detected numbers.

## Setup
### mnist-sphog
mnist-sphog is available to download at [http://ttic.uchicago.edu/~smaji/projects/digits/](http://ttic.uchicago.edu/~smaji/projects/digits/) as a compressed file.

**Important:** Once the file is decompressed, if the folder created is not named *mnist-sphog*, it must be renamed as such. Then, the folder should be moved to the directory containing the extractor code. For example, if the extractor code files are located at "/.../extractors/handwritten_numbers_extractor", then the path to the mnist-sphog folder should be "/.../extractors/handwritten_numbers_extractor/mnist-sphog".

### Matlab
Matlab must be installed in your system and typing *matlab* in your terminal should open Matlab (i.e. Matlab must be in your PATH).

## Advanced settings
The mnist-sphog code uses a trained model (*model_intersect.mat*) to recognize handwritten numbers. The quality of the model can be improved by retraining it with more images.

More information about the classifier can be found at the [mnist-sphog](http://ttic.uchicago.edu/~smaji/projects/digits/) website. The NIST data available for training can be found [here](http://yann.lecun.com/exdb/mnist/).

