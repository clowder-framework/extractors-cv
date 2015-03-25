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

# name to show in rabbitmq queue list
extractorName = "ncsa.cv.profiles"

# URL to be used for connecting to rabbitmq
rabbitmqURL = None

# name of rabbitmq exchange
rabbitmqExchange = "medici"

# type of files to process
messageType = "*.file.image.#"

# trust certificates, set this to false for self signed certificates
sslVerify=False

# path to opencv pretrained classifiers
profileface_cascade_path='/usr/local/share/OpenCV/haarcascades/haarcascade_profileface.xml'
        				#'/opt/local/share/OpenCV/haarcascades/haarcascade_profileface.xml'

