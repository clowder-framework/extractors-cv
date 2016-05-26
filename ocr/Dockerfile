# NCSA Brown Dog Project. Clowder OCR Python Extractor.
#
# Version: 0.1

# FROM clowder/python-base
FROM ncsa/clowder-extractors-python-base
MAINTAINER Rui Liu <ruiliu@illinois.edu>

ENV CLOWDER_HOME=/home/clowder \
    EXTRACTOR_HOME=/home/clowder/extractors-cv/ocr \
    RABBITMQ_URI="" \
    RABBITMQ_EXCHANGE=""

USER clowder
RUN cd ${CLOWDER_HOME} && \
    git clone https://opensource.ncsa.illinois.edu/stash/scm/cats/extractors-cv.git && \
    cd extractors-cv && \
    git checkout feature/BD-1079-update-OCR-extractor

USER root
RUN apt-get update && \
    apt-get install -y tesseract-ocr

# COPY does not honor the USER setting, so the owner is always root.
COPY start.sh ${EXTRACTOR_HOME}/

WORKDIR ${EXTRACTOR_HOME}
ENTRYPOINT ["./start.sh"]
