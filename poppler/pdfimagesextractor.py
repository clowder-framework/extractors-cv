#!/usr/bin/env python
import pika
import requests
import sys
import logging
import time
import json
import subprocess
import tempfile
import os
from config import *

# ----------------------------------------------------------------------
# BEGIN CONFIGURATION
# ----------------------------------------------------------------------

# name where rabbitmq is running
rabbitmqHost = "localhost"

# name to show in rabbitmq queue list
exchange = "medici"

# name to show in rabbitmq queue list
extractorName = "pdfimagesextractor"

# username and password to connect to rabbitmq
rabbitmqUsername = None
rabbitmqPassword = None

# accept any type of file
messageType = "*.file.pdf.#"

# set the path to pdfimages
pdfimagespath = '/usr/bin/pdfimages'

# trust certificates, set this to false for self signed certificates
sslVerify=False

# ----------------------------------------------------------------------
# END CONFIGURATION
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# setup connection to server and wait for messages
def connect_message_bus():
    """Connect to message bus and wait for messages"""
    global extractorName, rabbitmqUsername, rabbitmqURL, rabbitmqPort, rabbitmqPassword, messageType, exchange, rabbitmqHost


    # connect to rabbitmq using input rabbitmqUsername and rabbitmqPassword
    if (rabbitmqURL is None):
        if (rabbitmqUsername is not None and rabbitmqPassword is not None):
            credentials = pika.PlainCredentials(rabbitmqUsername, rabbitmqPassword)
        else:
            credentials = None
        parameters = pika.ConnectionParameters(host=rabbitmqHost, port=rabbitmqPort, credentials=credentials)
    else:
        parameters = pika.URLParameters(rabbitmqURL)
    connection = pika.BlockingConnection(parameters)

    
    # connect to channel
    channel = connection.channel()
    
    # declare the exchange in case it does not exist
    channel.exchange_declare(exchange=exchange, exchange_type='topic', durable=True)
    
    # declare the queue in case it does not exist
    channel.queue_declare(queue=extractorName, durable=True)

    # connect queue and exchange
    channel.queue_bind(queue=extractorName, exchange=exchange, routing_key=messageType)

    # create listener
    channel.basic_consume(on_message, queue=extractorName, no_ack=False)

    # start listening
    logger.info("Waiting for messages. To exit press CTRL+C")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()

    # close connection
    connection.close()
 
# ----------------------------------------------------------------------
# Process any incoming message
def on_message(channel, method, header, body):
    """When message is received do the following steps:
    1. download the file
    2. launch extractor function"""

    global logger, extractorName

    inputfile=None
    fileid=0

    try:
        # parse body back from json
        jbody=json.loads(body)
        host=jbody['host']
        fileid=jbody['id']
        secretKey=jbody['secretKey']
        intermediatefileid=jbody['intermediateId']
        datasetid=jbody['datasetId']
        if not (host.endswith('/')):
            host += '/'
        
         # tell everybody we are starting to process the file
        status_update(channel, header, fileid, "Started processing file")

        # download file
        inputfile = download_file(channel, header, host, secretKey, fileid, intermediatefileid)

        # call actual extractor function
        process_file(channel, header, host, secretKey, fileid, intermediatefileid, datasetid, inputfile)
 
        # notify rabbitMQ we are done processsing message
        channel.basic_ack(method.delivery_tag)

    except subprocess.CalledProcessError as e:
        msg = str.format("Error processing [exit code=%d]\n%s", e.returncode, e.output)
        logger.exception("[%s] %s", fileid, msg)
        status_update(channel, header, fileid, msg)
    except:
        logger.exception("[%s] error processing", fileid)
        status_update(channel, header, fileid, "Error processing")
    finally:
        status_update(channel, header, fileid, "Done")
        if inputfile is not None:
            try:
                os.remove(inputfile)
            except OSError:
                pass
            except UnboundLocalError:
                pass

# ----------------------------------------------------------------------
# Send updates about status of processing file
def status_update(channel, header, fileid, status):
    """Send notification on message bus with update"""

    global extractorName, exchange

    logger.debug("[%s] : %s", fileid, status)

    statusreport = {}
    statusreport['file_id'] = fileid
    statusreport['extractor_id'] = extractorName
    statusreport['status'] = status
    statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    channel.basic_publish(exchange=exchange,
                          routing_key=header.reply_to,
                          properties=pika.BasicProperties(correlation_id = header.correlation_id),
                          body=json.dumps(statusreport))

# ----------------------------------------------------------------------
# Download file from medici
def download_file(channel, header, host, key, fileid, intermediatefileid):
    """Download file to be processed from Medici"""

    global sslVerify

    status_update(channel, header, fileid, "Downloading file.")

    # fetch data
    url=host + 'api/files/' + intermediatefileid + '?key=' + key
    r=requests.get('%sapi/files/%s?key=%s' % (host, intermediatefileid, key),
                   stream=True, verify=sslVerify)
    r.raise_for_status()
    (fd, inputfile)=tempfile.mkstemp()
    with os.fdopen(fd, "w") as f:
        for chunk in r.iter_content(chunk_size=10*1024):
            f.write(chunk)
    return inputfile


# ----------------------------------------------------------------------
# Process the file and upload the results
def process_file(channel, header, host, key, fileid, intermediatefileid, datasetid, inputfile):
    """Extract images from file with pdfimages"""

    global sslVerify, extractorName, pdfimagespath

    status_update(channel, header, fileid, "Using poppler pdfimages to process file")

    
    (dirname, filename) = os.path.split(inputfile)
    basename = filename+"-image"
    basefolder=os.path.dirname(os.path.realpath(__file__))

    # call actual program
    output = subprocess.check_output([pdfimagespath, '-j', '-p', inputfile, basename], stderr=subprocess.STDOUT);

    # upload each of the images extracted
    for f in os.listdir(basefolder):
        if f.startswith(basename):
            p = os.path.join(basefolder,f)
            # print p

            # upload the file to the dataset
            url=host+'api/uploadToDataset/'+datasetid+'?key=' + key
            with open(p, 'rb') as f:
                files={"File" : f}
                r = requests.post(url, files=files, verify=sslVerify)
                r.raise_for_status()

            uploadedfileid = r.json()['id']
            logger.debug("[%s] extracted image file posted", uploadedfileid)

            os.remove(p)

    # metadata = {}
    # metadata["extractor_id"] = extractorName

    # headers={'Content-Type': 'application/json'}
    # r = requests.post('%sapi/files/%s/metadata?key=%s' % (host, fileid, key),
    #                   headers=headers,
    #                   data=json.dumps(metadata),
    #                   verify=sslVerify);
    # r.raise_for_status()


if __name__ == '__main__':
    # configure the logging system
    logging.basicConfig(format="%(asctime)-15s %(name)-10s %(levelname)-7s : %(message)s",
                        level=logging.WARN)
    logger = logging.getLogger(extractorName)
    logger.setLevel(logging.DEBUG)

    # connect and process data    
    sys.exit(connect_message_bus())