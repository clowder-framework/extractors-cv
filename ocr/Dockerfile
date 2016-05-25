# NCSA Brown Dog Project. Clowder OCR Python Extractor.
#
# Version: 0.1

# FROM clowder/python-base
FROM ncsa/clowder-python-base
MAINTAINER Rui Liu <ruiliu@illinois.edu>

ENV CLOWDER_HOME=/home/clowder \
    EXTRACTOR_HOME=/home/clowder/extractors-cv/ocr \
    RABBITMQ_URI="" \
    RABBITMQ_EXCHANGE=""

USER clowder
RUN cd ${CLOWDER_HOME} && \
    git clone https://opensource.ncsa.illinois.edu/stash/scm/cats/extractors-cv.git

USER root
RUN apt-get install -y tesseract-ocr

# COPY does not honor the USER setting, so the owner is always root, thus requiring chown.
COPY start.sh ${EXTRACTOR_HOME}/
RUN chown clowder.nogroup ${EXTRACTOR_HOME}/start.sh
RUN chmod 755 ${EXTRACTOR_HOME}/start.sh

WORKDIR ${EXTRACTOR_HOME}
CMD ["./start.sh"]
