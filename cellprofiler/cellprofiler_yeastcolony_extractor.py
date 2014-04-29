#!/usr/bin/env python
import pika
import sys
import logging
import json
import traceback
import requests
import tempfile
import subprocess
import os
import itertools
import time
import zipfile
import os.path
import shutil

def main():
    global logger

    # name of receiver
    receiver='ncsa.cellprofiler.zip'

    # configure the logging system
    logging.basicConfig(format="%(asctime)-15s %(name)-10s %(levelname)-7s : %(message)s", level=logging.WARN)
    logger = logging.getLogger(receiver)
    logger.setLevel(logging.DEBUG)

    # connect to rabitmq
    connection = pika.BlockingConnection()



    # connect to channel
    channel = connection.channel()

    # declare the exchange
    channel.exchange_declare(exchange='medici', exchange_type='topic', durable=True)

    # declare the queue
    channel.queue_declare(queue=receiver, durable=True)

    # connect queue and exchange
    channel.queue_bind(queue=receiver, exchange='medici', routing_key='*.file.multi.files-zipped.#')

    # create listener
    channel.basic_consume(on_message, queue=receiver, no_ack=False)

    # start listening
    logger.info("Waiting for messages. To exit press CTRL+C")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()

    # close connection
    connection.close()


def extract_cellprofiler(inputfile, host, fileid, datasetid, key):
    global logger
    logger.debug("Running cellprofiler yeast colonies dataset extractor")
    # (fd, thumbnailfile)=tempfile.mkstemp(suffix='.' + ext)
    try:
       
        basefolder=os.path.dirname(os.path.realpath(__file__))
        pipelinepath=os.path.join(basefolder, "ExampleYeastColonies_BT.cp")
        datasetinputfolder=os.path.join(basefolder, datasetid+"_yeast_input")
        datasetoutputfolder=os.path.join(basefolder, datasetid+"_yeast_output")
        
        zfile = zipfile.ZipFile(inputfile)
        if not os.path.exists(datasetinputfolder):
            os.makedirs(datasetinputfolder)
        if not os.path.exists(datasetoutputfolder):
            os.makedirs(datasetoutputfolder)
        
        
        dir1 = ""
        dir2 = ""
        count1 = 0
        count2 = 0
        for name in zfile.namelist():
            (dirname, filename) = os.path.split(name)

            if filename=="6-1.jpg" or filename=="PlateTemplate.png":
                dirname=os.path.join(datasetinputfolder, dirname)
                if filename == "6-1.jpg":
                    dir1 = dirname
                    count1 +=1
                if filename == "PlateTemplate.png":
                    dir2 = dirname
                    count2 +=1
                print "Decompressing " + filename + " on " + dirname
                zfile.extract(name, datasetinputfolder)
                
        if count1==1 and count2==1 and dir1 == dir2:
            
            subprocess.check_output(['CellProfiler.exe', '-c', '-r', '-i',  dir1, '-o', datasetoutputfolder, '-p', pipelinepath], stderr=subprocess.STDOUT)
    
            logger.debug("[%s] cellprofiler pipeline processed", datasetid)
            for f in os.listdir(datasetoutputfolder):
                print os.path.join(datasetoutputfolder,f)
                if f.endswith(".csv") or f.endswith(".png"):
                    # upload the file to the dataset
                    url=host+'api/uploadToDataset/'+datasetid+'?key=' + key
                    r = requests.post(url, files={"File" : open(os.path.join(datasetoutputfolder,f), 'rb')})
                    r.raise_for_status()
                    uploadedfileid = r.json()['id']
                    logger.debug("[%s] cellprofiler result file posted", uploadedfileid)
     

            logger.debug("[%s] cellprofiler pipeline results posted", datasetid)

        else:
            logger.debug("[%s] files did not match this extractor requirements", datasetid)

    finally:
        if os.path.isdir(datasetinputfolder):
            try:
                shutil.rmtree(datasetinputfolder)
            except:
                pass
        if os.path.isdir(datasetoutputfolder):
            try:
                shutil.rmtree(datasetoutputfolder)
            except:
                pass

        logger.debug("[%s] done with cellprofiler pipeline", datasetid)
                
        
def on_message(channel, method, header, body):
    global logger
    statusreport = {}

    inputfile=None
    try:
        # parse body back from json
        jbody=json.loads(body)

        # key=jbody['key']
        key='r1ek3rs'
        host=jbody['host']
        logger.debug("host[%s]=",host)
        fileid=jbody['id']
        datasetid=jbody['datasetId']
        if not (host.endswith('/')):
            host += '/'

        # print what we are doing
        logger.debug("[%s] started processing", datasetid)

        # for status reports
        statusreport['file_id'] = fileid
        statusreport['extractor_id'] = 'ncsa.cellprofiler.zip'
        statusreport['status'] = 'Downloading input file.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        channel.basic_publish(exchange='',
                            routing_key=header.reply_to,
                            properties=pika.BasicProperties(correlation_id = \
                                                        header.correlation_id),
                            body=json.dumps(statusreport)) 


        # fetch data
        url=host + 'api/files/' + fileid + '?key=' + key
        r=requests.get(url, stream=True)
        r.raise_for_status()
        (fd, inputfile)=tempfile.mkstemp()
        with os.fdopen(fd, "w") as f:
            for chunk in r.iter_content(chunk_size=10*1024):
                f.write(chunk)

        statusreport['status'] = 'Detecting cellprofiler pipeline metadata and associating with file.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        channel.basic_publish(exchange='',
                            routing_key=header.reply_to,
                            properties=pika.BasicProperties(correlation_id = \
                                                        header.correlation_id),
                            body=json.dumps(statusreport))


        extract_cellprofiler(inputfile, host, fileid, datasetid, key)
        

        # Ack
        channel.basic_ack(method.delivery_tag)
        logger.debug("[%s] finished processing", datasetid)
    except subprocess.CalledProcessError as e:
        logger.exception("[%s] error processing [exit code=%d]\n%s", datasetid, e.returncode, e.output)
        statusreport['status'] = 'Error processing.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S') 
        channel.basic_publish(exchange='',
                routing_key=header.reply_to,
                properties=pika.BasicProperties(correlation_id = \
                                                header.correlation_id),
                body=json.dumps(statusreport)) 

    except:
        logger.exception("[%s] error processing", datasetid)
        statusreport['status'] = 'Error processing.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S') 
        channel.basic_publish(exchange='',
                routing_key=header.reply_to,
                properties=pika.BasicProperties(correlation_id = \
                                                header.correlation_id),
                body=json.dumps(statusreport)) 
    finally:
        statusreport['status'] = 'DONE.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        channel.basic_publish(exchange='',
                            routing_key=header.reply_to,
                            properties=pika.BasicProperties(correlation_id = \
                                                        header.correlation_id),
                            body=json.dumps(statusreport))
        # if inputfile is not None and os.path.isfile(inputfile):
        #     os.remove(inputfile)


if __name__ == "__main__":
    main()