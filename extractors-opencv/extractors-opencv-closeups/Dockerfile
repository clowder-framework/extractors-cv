# NCSA Brown Dog Project. Clowder OpenCV human eye detection Python Extractor.
#
# Version: 1.0

FROM clowder/pyclowder:1
MAINTAINER Rui Liu <ruiliu@illinois.edu>

ENV CLOWDER_HOME=/home/clowder \
    RABBITMQ_URI="" \
    RABBITMQ_EXCHANGE="clowder" \
    MAIN_SCRIPT="closeup.py"

# Install the requied software.
USER root
RUN apt-get update && \
    apt-get install -y python-opencv opencv-data

# COPY does not honor the USER setting, so the owner is always root.
COPY *.sh ${MAIN_SCRIPT} config.py extractor_info.json ${CLOWDER_HOME}/

ENTRYPOINT ["/home/clowder/entrypoint.sh"]
CMD ["extractor"]
