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
extractorName = os.getenv('RABBITMQ_QUEUE', "ncsa.cv.closeups")

# URL to be used for connecting to rabbitmq
rabbitmqURL = os.getenv('RABBITMQ_URI', "amqp://guest:guest@localhost:5672/%2f")

# name of rabbitmq exchange
rabbitmqExchange = os.getenv('RABBITMQ_EXCHANGE', "clowder")

# type of files to process
messageType = "*.file.image.#", "extractors."+extractorName

# trust certificates, set this to false for self signed certificates
sslVerify = os.getenv('RABBITMQ_SSLVERIFY', False)

# path to opencv pretrained classifiers
# Location where brew installed on Mac OSX 64bit.
face_cascade_path = '/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt.xml'
# Location in the "opencv-data" package on Ubuntu 14.04.
# face_cascade_path = '/usr/share/opencv/haarcascades/haarcascade_frontalface_alt.xml'
profileface_cascade_path = '/usr/local/share/OpenCV/haarcascades/haarcascade_profileface.xml'

# Endpoints and keys for registering extractor information in CSV format.
registrationEndpoints = os.getenv('REGISTRATION_ENDPOINTS', "http://localhost:9000/clowder/api/extractors?key=key1,http://host2:9000/api/extractors?key=key2")
