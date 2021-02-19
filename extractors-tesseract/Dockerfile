FROM ubuntu:20.04

LABEL maintainer="Bing Zhang <bing@illinois.edu>"

ENV RABBITMQ_QUEUE="ncsa.image.ocr" \
    RABBITMQ_URI="" \
    RABBITMQ_EXCHANGE="clowder" \
    MAIN_SCRIPT="ocr.py"

WORKDIR /home/clowder
COPY entrypoint.sh ocr.py extractor_info.json /home/clowder/

RUN apt-get update && \
    DEBIAN_FRONTEND="noninteractive" apt-get install -y tzdata \
    -y tesseract-ocr \
    -y python3-pip

COPY requirements.txt .
RUN pip3 install -r requirements.txt

ENTRYPOINT ["/home/clowder/entrypoint.sh"]
CMD ["extractor"]
