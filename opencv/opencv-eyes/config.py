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
extractorName = "ncsa.cv.eyes"

# address of host where rabbitmq is running
rabbitmqHost = "localhost"

# username and password to connect to rabbitmq
rabbitmqUsername = None
rabbitmqPassword = None

# name of rabbitmq exchange
exchange = "medici"

# type of files to process
messageType = "*.file.image.#"

# trust certificates, set this to false for self signed certificates
sslVerify=False

# path to opencv pretrained classifiers
face_cascade_path = '/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt.xml'
					#'/opt/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt.xml'
big_eyepair_cascade_path = '/usr/local/share/OpenCV/haarcascades/haarcascade_mcs_eyepair_big.xml'
							#'/opt/local/share/OpenCV/haarcascades/haarcascade_mcs_eyepair_big.xml'
small_eyepair_cascade_path = '/usr/local/share/OpenCV/haarcascades/haarcascade_mcs_eyepair_small.xml'
							#'/opt/local/share/OpenCV/haarcascades/haarcascade_mcs_eyepair_small.xml'
left_eye_cascade_path = '/usr/local/share/OpenCV/haarcascades/haarcascade_lefteye_2splits.xml'
						#'/opt/local/share/OpenCV/haarcascades/haarcascade_lefteye_2splits.xml'
right_eye_cascade_path = '/usr/local/share/OpenCV/haarcascades/haarcascade_righteye_2splits.xml'
						#'/opt/local/share/OpenCV/haarcascades/haarcascade_righteye_2splits.xml'
