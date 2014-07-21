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
import csv

def main():
    global logger, receiver

    # name of receiver
    receiver='ncsa.cellprofiler.trackobject'

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
    global logger, receiver
    logger.debug("Running cellprofiler ExampleTrackObjects pipeline")
    # (fd, thumbnailfile)=tempfile.mkstemp(suffix='.' + ext)
    try:
       
        basefolder=os.path.dirname(os.path.realpath(__file__))
        pipelinepath=os.path.join(basefolder, "ExampleTrackObjects.cp")
        datasetinputfolder=os.path.join(basefolder, datasetid+"_track_input")
        datasetoutputfolder=os.path.join(basefolder, datasetid+"_track_output")
        
        zfile = zipfile.ZipFile(inputfile)
        if not os.path.exists(datasetinputfolder):
            os.makedirs(datasetinputfolder)
        if not os.path.exists(datasetoutputfolder):
            os.makedirs(datasetoutputfolder)
        
        
        indir = ""
        count=0
        for name in zfile.namelist():
            (dirname, filename) = os.path.split(name)

            if filename.find("GFPHistone")!=-1 and not filename.startswith("."):
                dirname=os.path.join(datasetinputfolder, dirname)
                print "Decompressing " + filename + " on " + dirname
                zfile.extract(name, datasetinputfolder)
                indir = dirname
                count+=1
                
        if count>0:
            subprocess.check_output(['CellProfiler.exe', '-c', '-r', '-i',  indir, '-o', datasetoutputfolder, '-p', pipelinepath], stderr=subprocess.STDOUT)
    
            logger.debug("[%s] cellprofiler pipeline processed", datasetid)
            datasetoutputfolder2 = os.path.join(datasetoutputfolder,  datasetid+"_track_input")
            for f in sorted(os.listdir(datasetoutputfolder2)):
                print os.path.join(datasetoutputfolder2,f)
                if f.lower().endswith(".csv") or f.lower().endswith(".png"):
                    # upload the file to the dataset
                    url=host+'api/uploadToDataset/'+datasetid+'?key=' + key
                    r = requests.post(url, files={"File" : open(os.path.join(datasetoutputfolder2,f), 'rb')})
                    r.raise_for_status()
                    uploadedfileid = r.json()['id']
                    logger.debug("[%s] cellprofiler result file posted", uploadedfileid)
     

            mdata = {}
            mdata["extractor_id"]=receiver
            for f in os.listdir(datasetoutputfolder2):
                filemeta={}
                filepath = os.path.join(datasetoutputfolder2,f)
                if f.endswith(".csv"):
                    metarows=[]
                    with open(filepath, 'rb') as csvfile:
                        reader = csv.reader(csvfile, delimiter=',')
                        header = reader.next()
                        for row in reader:
                            metarow={}
                            for cell in range(0, len(row)-1):
                                metarow[header[cell]]=row[cell]
                            metarows.append(metarow)
                    metafield=f[f.rindex('_')+1:f.rindex('.')]
                    mdata[metafield]=metarows
            
            headers={'Content-Type': 'application/json'}
            url=host+'api/files/'+ fileid +'/metadata?key=' + key
            rt = requests.post(url, headers=headers, data=json.dumps(mdata))
            rt.raise_for_status()


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
    global logger, receiver
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
        statusreport['extractor_id'] = receiver
        statusreport['status'] = 'Downloading input file.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')
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
        statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')
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
        statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S') 
        channel.basic_publish(exchange='',
                routing_key=header.reply_to,
                properties=pika.BasicProperties(correlation_id = \
                                                header.correlation_id),
                body=json.dumps(statusreport)) 

    except:
        logger.exception("[%s] error processing", datasetid)
        statusreport['status'] = 'Error processing.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S') 
        channel.basic_publish(exchange='',
                routing_key=header.reply_to,
                properties=pika.BasicProperties(correlation_id = \
                                                header.correlation_id),
                body=json.dumps(statusreport)) 
    finally:
        statusreport['status'] = 'DONE.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')
        channel.basic_publish(exchange='',
                            routing_key=header.reply_to,
                            properties=pika.BasicProperties(correlation_id = \
                                                        header.correlation_id),
                            body=json.dumps(statusreport))
        if inputfile is not None and os.path.isfile(inputfile):
            os.remove(inputfile)


if __name__ == "__main__":
    main()