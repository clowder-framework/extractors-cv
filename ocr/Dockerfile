# NCSA Brown Dog Project. Clowder OCR Python Extractor.
#
# Version: 0.1

# FROM clowder/python-base
FROM ncsa/clowder-extractors-python-base
MAINTAINER Rui Liu <ruiliu@illinois.edu>

# Defaults to the "master" branch if not given.
ENV CLOWDER_HOME=/home/clowder \
    RABBITMQ_URI="" \
    RABBITMQ_EXCHANGE=""

USER root
RUN apt-get update && \
    apt-get install -y tesseract-ocr

# COPY does not honor the USER setting, so the owner is always root.
COPY start.sh ocr.py config.py extractor_info.json ${CLOWDER_HOME}/

WORKDIR ${CLOWDER_HOME}
ENTRYPOINT ["./start.sh"]
