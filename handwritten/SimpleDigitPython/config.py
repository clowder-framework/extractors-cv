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
extractorName = "ncsa.image.digitpy"

# URL to be used for connecting to rabbitmq
rabbitmqURL = None

# address of host where rabbitmq is running
rabbitmqHost = "localhost"

#port to be used for connecting to rabbitmq
rabbitmqPort = 5672

# username and password to connect to rabbitmq
rabbitmqUsername = None
rabbitmqPassword = None

# name of rabbitmq exchange
exchange = "medici"

# type of files to process
messageType = "*.file.image.#"

# trust certificates, set this to false for self signed certificates
sslVerify=False
