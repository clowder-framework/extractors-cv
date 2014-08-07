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
import xmltodict
from xml.dom.minidom import parse, parseString

sslVerify=False


def main():
    global logger
    global receiver
    global bisqueuser
    global bisquepassword

    bisqueuser=''
    bisquepassword=''
    # name of receiver
    receiver='ncsa.bisque.metadata'

    # configure the logging system
    logging.basicConfig(format="%(asctime)-15s %(name)-10s %(levelname)-7s : %(message)s", level=logging.WARN)
    logger = logging.getLogger(receiver)
    logger.setLevel(logging.DEBUG)

    # connect to rabitmq
    connection = pika.BlockingConnection()

    # # connect to rabbitmq running on server
    # parameters = pika.URLParameters('amqp://'+username+':'+password+'@'+servername+':'+portnum+'/%2F') #portnum=5672
    # connection = pika.BlockingConnection(parameters)

    # connect to channel
    channel = connection.channel()

    # declare the exchange
    channel.exchange_declare(exchange='medici', exchange_type='topic', durable=True)

    # declare the queue
    channel.queue_declare(queue=receiver, durable=True)

    # connect queue and exchange
    channel.queue_bind(queue=receiver, exchange='medici', routing_key='*.file.image.#')

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
 

def call_bisque(filename):
    global bisqueuser
    global bisquepassword
    
    metadict ={}
    posturl = 'http://bisque.ece.ucsb.edu/import/transfer'
    files = {'file': open(filename, 'rb')}
    r = requests.post(posturl, files=files , auth=(bisqueuser, bisquepassword))

    if(r.status_code==200):
        xmldoc = parseString(r.text)
        imagelist =  xmldoc.getElementsByTagName('image')
        imageuri = imagelist[0].attributes['uri'].value
        imageuniq = imagelist[0].attributes['resource_uniq'].value


        r = requests.get('http://bisque.ece.ucsb.edu/image_service/'+imageuniq+'?meta', auth=(bisqueuser, bisquepassword))

        metadict = xmltodict.parse(r.text) #dict containing xml fields
        # metajson = json.dumps(metadict) #json object

        r = requests.delete(imageuri, auth=(bisqueuser, bisquepassword))

    return metadict['resource']#metadict
    
    


def extract_bisque(inputfile, host, fileid, key):
    global logger
    global sslVerify
    
    logger.debug("INSIDE: extract_Bisque")
    
    try:
        bisquedict = call_bisque(inputfile)

        headers={'Content-Type': 'application/json'}

        url=host+'api/files/'+ fileid +'/metadata?key=' + key
        mdata={}
        mdata["bisque_metadata"]=[bisquedict]

        # logger.debug("metadata: %s",json.dumps(mdata))
        rt = requests.post(url, headers=headers, data=json.dumps(mdata), verify=sslVerify)
        rt.raise_for_status()
        logger.debug("[%s] Bisque metadata extractor performed successfully", fileid)

    finally:
        logger.debug("[%s] done with Bisque metadata extractor", fileid)  
        

def on_message(channel, method, header, body):
    global logger
    global receiver
    global sslVerify

    statusreport = {}

    inputfile=None
    try:
        # parse body back from json
        jbody=json.loads(body)
        key=jbody['key']
        host=jbody['host']
        #logger.debug("host[%s]=",host)
        fileid=jbody['id']
        if not (host.endswith('/')):
            host += '/'

        # print what we are doing
        logger.debug("[%s] started processing", fileid)
        # for status reports
        statusreport['file_id'] = fileid
        statusreport['extractor_id'] = receiver
        statusreport['status'] = 'Downloading image file.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        statusreport['end'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        channel.basic_publish(exchange='',
                            routing_key=header.reply_to,
                            properties=pika.BasicProperties(correlation_id = \
                                                        header.correlation_id),
                            body=json.dumps(statusreport)) 

        # fetch data
        url=host + 'api/files/' + fileid + '?key=' + key
        r=requests.get(url, stream=True, verify=sslVerify)
        r.raise_for_status()
        (fd, inputfile)=tempfile.mkstemp()
        with os.fdopen(fd, "w") as f:
            for chunk in r.iter_content(chunk_size=10*1024):
                f.write(chunk)

        statusreport['status'] = 'calling Bisque and associating results with file.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        statusreport['end'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        channel.basic_publish(exchange='',
                            routing_key=header.reply_to,
                            properties=pika.BasicProperties(correlation_id = \
                                                        header.correlation_id),
                            body=json.dumps(statusreport))



        extract_bisque(inputfile, host, fileid, key)
        

    except subprocess.CalledProcessError as e:
        logger.exception("[%s] error processing [exit code=%d]\n%s", fileid, e.returncode, e.output)
        statusreport['status'] = 'Error processing.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        statusreport['end'] = time.strftime('%Y-%m-%dT%H:%M:%S') 
        channel.basic_publish(exchange='',
                routing_key=header.reply_to,
                properties=pika.BasicProperties(correlation_id = \
                                                header.correlation_id),
                body=json.dumps(statusreport)) 
    except:
        logger.exception("[%s] error processing", fileid)
        statusreport['status'] = 'Error processing.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        statusreport['end'] = time.strftime('%Y-%m-%dT%H:%M:%S') 
        channel.basic_publish(exchange='',
                routing_key=header.reply_to,
                properties=pika.BasicProperties(correlation_id = \
                                                header.correlation_id),
                body=json.dumps(statusreport)) 
    finally:
        statusreport['status'] = 'DONE.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        statusreport['end'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        channel.basic_publish(exchange='',
                            routing_key=header.reply_to,
                            properties=pika.BasicProperties(correlation_id = \
                                                        header.correlation_id),
                            body=json.dumps(statusreport))
        if inputfile is not None:
            os.remove(inputfile)


        # Ack
        channel.basic_ack(method.delivery_tag)
        logger.debug("[%s] finished processing", fileid)


if __name__ == "__main__":
    main()
