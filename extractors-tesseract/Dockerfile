# NCSA Brown Dog Project. Clowder OCR Python Extractor.
#
# Version: 0.1

# FROM clowder/python-base
FROM clowder/pyclowder:1
MAINTAINER Rui Liu <ruiliu@illinois.edu>

# Defaults to the "master" branch if not given.
ENV CLOWDER_HOME=/home/clowder \
    RABBITMQ_URI="" \
    RABBITMQ_EXCHANGE="clowder" \
    MAIN_SCRIPT="ocr.py"

USER root
RUN apt-get update && \
    apt-get install -y tesseract-ocr

# COPY does not honor the USER setting, so the owner is always root.
COPY *.sh ocr.py config.py extractor_info.json ${CLOWDER_HOME}/

ENTRYPOINT ["/home/clowder/entrypoint.sh"]
CMD ["extractor"]
