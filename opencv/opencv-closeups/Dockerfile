# NCSA Brown Dog Project. Clowder OpenCV human eye detection Python Extractor.
#
# Version: 1.0

FROM ncsa/clowder-extractors-python-base
MAINTAINER Rui Liu <ruiliu@illinois.edu>

ENV CLOWDER_HOME=/home/clowder \
    RABBITMQ_URI="" \
    RABBITMQ_EXCHANGE="" \
    MAIN_SCRIPT="closeup.py"

# Install the requied software.
USER root
RUN apt-get update && \
    apt-get install -y python-opencv opencv-data

# COPY does not honor the USER setting, so the owner is always root.
COPY start.sh ${MAIN_SCRIPT} config.py extractor_info.json ${CLOWDER_HOME}/

# Fix the default paths.
RUN sed -i -e "s#/usr/local/share/OpenCV#/usr/share/opencv#" ${CLOWDER_HOME}/config.py

WORKDIR ${CLOWDER_HOME}
ENTRYPOINT ["./start.sh"]
