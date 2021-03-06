# NCSA Brown Dog Project. Clowder Historic Map River Python Extractor.
# Version: 1.0

# FROM clowder/python-base
FROM clowder/pyclowder:1
MAINTAINER Smruti Padhy <spadhy@illinois.edu>

# Setup environment variables. These are passed into the container. You can change
# these to your setup. If RABBITMQ_URI is not set, it will try and use the rabbitmq
# server that is linked into the container. MAIN_SCRIPT is set to the script to be
# executed by entrypoint.sh

ENV RABBITMQ_URI="" \
    RABBITMQ_EXCHANGE="clowder" \
    RABBITMQ_VHOST="%2F" \
    RABBITMQ_QUEUE="ncsa.cv.river" \
    REGISTRATION_ENDPOINTS="https://clowder.ncsa.illinois.edu/extractors" \
    MAIN_SCRIPT="river.py"

# Install any programs needed

USER root
RUN apt-get update && apt-get install -y \
    python-opencv opencv-data \
    imagemagick \
    software-properties-common \
    gdal-bin \
    python-gdal
    

# Switch to clowder, copy files and be ready to run
USER clowder

# command to run when starting docker
COPY entrypoint.sh *.py extractor_info.json /home/clowder/

ENTRYPOINT ["/home/clowder/entrypoint.sh"]
CMD ["extractor"]
