# NCSA Brown Dog Project. Clowder OpenCV face detection Python Extractor.
#
# Version: 0.1

# FROM clowder/python-base
FROM ncsa/clowder-extractors-python-base
MAINTAINER Rui Liu <ruiliu@illinois.edu>

# Defaults to the "master" branch if not given.
ARG GIT_BRANCH=master
ENV CLOWDER_HOME=/home/clowder \
    EXTRACTOR_HOME=/home/clowder/extractors-cv/opencv/opencv-faces \
    RABBITMQ_URI="" \
    RABBITMQ_EXCHANGE=""

# Get git source, fix the default paths.
USER clowder
RUN cd ${CLOWDER_HOME} && \
    git clone https://opensource.ncsa.illinois.edu/stash/scm/cats/extractors-cv.git && \
    cd extractors-cv && \
    git checkout $GIT_BRANCH && \
    sed -i -e "s#/usr/local/share/OpenCV#/usr/share/opencv#" ${EXTRACTOR_HOME}/config.py

# Install the requied software.
USER root
RUN apt-get update && \
    apt-get install -y python-opencv opencv-data

# COPY does not honor the USER setting, so the owner is always root.
COPY start.sh ${EXTRACTOR_HOME}/

WORKDIR ${EXTRACTOR_HOME}
ENTRYPOINT ["./start.sh"]
