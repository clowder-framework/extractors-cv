# =============================================================================
#
# In order for this extractor to run according to your preferences, 
# the following parameters need to be set. 
# 
# Some parameters can be left with the default values provided here - in that 
# case it is important to verify that the default value is appropriate to 
# your system. It is especially important to verify that paths to files and 
# software applications are valid in your system.
#
# =============================================================================

import os

# name to show in rabbitmq queue list
extractorName = os.getenv('RABBITMQ_QUEUE', "ncsa.cv.eyes")

# URL to be used for connecting to rabbitmq
rabbitmqURL = os.getenv('RABBITMQ_URI', "amqp://guest:guest@localhost:5672/%2f")

# name of rabbitmq exchange
rabbitmqExchange = os.getenv('RABBITMQ_EXCHANGE', "clowder")

# type of files to process
messageType = "*.file.image.#", "extractors."+extractorName

# trust certificates, set this to false for self signed certificates
sslVerify = os.getenv('RABBITMQ_SSLVERIFY', False)

# path to opencv pretrained classifiers
# Default to Ubuntu 14.04 location: "/usr/share/opencv".
# On Mac OSX, brew installs to "/usr/local/share/OpenCV".
opencv_path = os.getenv('OPENCV_PATH', "/usr/share/opencv")
face_cascade_path = opencv_path + '/haarcascades/haarcascade_frontalface_alt.xml'
big_eyepair_cascade_path = opencv_path + '/haarcascades/haarcascade_mcs_eyepair_big.xml'
small_eyepair_cascade_path = opencv_path + '/haarcascades/haarcascade_mcs_eyepair_small.xml'
left_eye_cascade_path = opencv_path + '/haarcascades/haarcascade_lefteye_2splits.xml'
right_eye_cascade_path = opencv_path + '/haarcascades/haarcascade_righteye_2splits.xml'

# Endpoints and keys for registering extractor information in CSV format.
registrationEndpoints = os.getenv('REGISTRATION_ENDPOINTS', "http://localhost:9000/clowder/api/extractors?key=key1,http://host2:9000/api/extractors?key=key2")
