# FROM clowder/python-base
FROM ncsa/clowder-extractors-python-base
MAINTAINER Rob Kooper <kooper@illinois.edu>

# Location where matlab will be mounted
VOLUME /matlab

# Setup environment variables. These are passed into the container. You can change
# these to your setup. If RABBITMQ_URI is not set, it will try and use the rabbitmq
# server that is linked into the container. MAIN_SCRIPT is set to the script to be
# executed by entrypoint.sh
ENV RABBITMQ_URI="" \
    RABBITMQ_EXCHANGE="clowder" \
    RABBITMQ_VHOST="%2F" \
    RABBITMQ_QUEUE="ncsa.cv.caltech101" \
    MATLAB_BINARY="/matlab/bin/matlab" \
    MAIN_SCRIPT="caltech101extractor.py" 

# Install any programs needed
USER root
RUN apt-get -qq -y update && apt-get -y install \
        libxext6 \
        libxmu6 \
        libxt6 \
        wget \
    && mkdir -p /matlab \
    && rm -rf /var/lib/apt/lists/*   

# Switch to clowder, copy files and be ready to run
USER clowder

# create vlfeat
COPY entrypoint.sh *.py *.json /home/clowder/
RUN wget -q -O /tmp/vlfeat-0.9.20-bin.tar.gz http://www.vlfeat.org/download/vlfeat-0.9.20-bin.tar.gz \
    && tar xf /tmp/vlfeat-0.9.20-bin.tar.gz -C /tmp \
    && mv /tmp/vlfeat-0.9.20 /home/clowder/vlfeat
COPY baseline-model.mat /home/clowder/vlfeat/apps/data/

# command to run when starting docker
ENTRYPOINT ["/home/clowder/entrypoint.sh"]
CMD ["extractor"]
