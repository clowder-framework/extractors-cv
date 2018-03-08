FROM clowder/pyclowder:2

MAINTAINER Bing Zhang <bing@illinois.edu>

ENV RABBITMQ_QUEUE="ncsa.image.ocr" \
    RABBITMQ_URI="" \
    RABBITMQ_EXCHANGE="clowder" \
    MAIN_SCRIPT="ocr.py"

COPY entrypoint.sh ocr.py extractor_info.json /home/clowder/

RUN apt-get update && \
    apt-get install -y tesseract-ocr

ENTRYPOINT ["/home/clowder/entrypoint.sh"]
CMD ["extractor"]
