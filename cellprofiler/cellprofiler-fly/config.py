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
extractorName = "ncsa.cellprofiler.fly"

# URL to be used for connecting to rabbitmq
rabbitmqURL = None

# name of rabbitmq exchange
rabbitmqExchange = "medici"

# type of files to process
messageType = "*.file.multi.files-zipped.#"

# trust certificates, set this to false for self signed certificates
sslVerify=False
