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
import numpy as np
import cv2
import time

sslVerify=False

def main():
    global logger
    global receiver
    # name of receiver
    receiver='ncsa.cv.closeup'

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
    channel.queue_bind(queue=receiver, exchange='medici', routing_key='*.file.image.#')

    # setting prefetch count to 1 as workarround pika 0.9.14
    channel.basic_qos(prefetch_count=1)

    # start listening
    logger.info("Waiting for messages. To exit press CTRL+C")

    # create listener
    channel.basic_consume(on_message, queue=receiver, no_ack=False)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()

    # close connection
    connection.close()
 


def detect_closeup(inputfile, ext, host, fileid, key):
    global logger
    global sslVerify

    logger.debug("INSIDE: detect_closeup")
    try:
        face_cascade = cv2.CascadeClassifier('/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt.xml')
        profile_face_cascade = cv2.CascadeClassifier('/usr/local/share/OpenCV/haarcascades/haarcascade_profileface.xml')
       
        #face_cascade = cv2.CascadeClassifier('/opt/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt.xml')
        #profile_face_cascade = cv2.CascadeClassifier('/opt/local/share/OpenCV/haarcascades/haarcascade_profileface.xml')
        
        img = cv2.imread(inputfile, cv2.CV_LOAD_IMAGE_GRAYSCALE)
        if img is not None:
            gray=img
            gray = cv2.equalizeHist(gray)
            
            imgh=len(gray)
            imgw=len(gray[0])
        
            midCloseUp=False
            fullCloseUp=False

            faces=face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=2, minSize=(imgw/8, imgh/8), flags=cv2.cv.CV_HAAR_SCALE_IMAGE)
            for (x,y,w,h) in faces:
                if ((w*h>=(imgw*imgh/3)) or (w>=0.8*imgw and h>=0.5*imgh) or (w>=0.5*imgw and h>=0.8*imgh)): #this is a closeup
                    fullCloseUp=True
            for (x,y,w,h) in faces: 
                if(w*h>=(imgw*imgh/8)): #this is a medium closeup
                    midCloseUp=True
            
            profilefaces=profile_face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=10, minSize=(imgw/8, imgh/8))
            for (x,y,w,h) in profilefaces:
                if ((w*h>=(imgw*imgh/3)) or (w>=0.8*imgw and h>=0.5*imgh) or (w>=0.5*imgw and h>=0.8*imgh)): #this is a closeup
                    fullCloseUp=True
            for (x,y,w,h) in profilefaces: 
                if(w*h>=(imgw*imgh/8)): #this is a medium closeup
                    midCloseUp=True


            headers={'Content-Type': 'application/json'}
            if fullCloseUp:
                url=host+'api/files/'+ fileid +'/tags?key=' + key
                mdata={}
                mdata["tags"]=["Full Close Up Automatically Detected"]
                mdata["extractor_id"]=receiver
                logger.debug("tags: %s",json.dumps(mdata))
                rt = requests.post(url, headers=headers, data=json.dumps(mdata), verify=sslVerify)
                rt.raise_for_status()
                logger.debug("[%s] created section and previews of type %s", fileid, ext)

            elif midCloseUp:
                url=host+'api/files/'+ fileid +'/tags?key=' + key
                mdata={}
                mdata["tags"]=["Mid Close Up Automatically Detected"]
                mdata["extractor_id"]=receiver
                logger.debug("tags: %s",json.dumps(mdata))
                rt = requests.post(url, headers=headers, data=json.dumps(mdata), verify=sslVerify)
                rt.raise_for_status()
                logger.debug("[%s] created section and previews of type %s", fileid, ext)        
    finally:
        #os.remove(previewfile)     
        logger.debug("done with closeups")  
        

def get_image_data(imagefile):
    global logger

    text=subprocess.check_output(['identify', imagefile], stderr=subprocess.STDOUT)
    return text

def on_message(channel, method, header, body):
    global logger
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
        statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')
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

        
        statusreport['status'] = 'Detecting closeup and tagging.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')
        channel.basic_publish(exchange='',
                            routing_key=header.reply_to,
                            properties=pika.BasicProperties(correlation_id = \
                                                        header.correlation_id),
                            body=json.dumps(statusreport))


        # create previews
        
        detect_closeup(inputfile, 'jpg', host, fileid, key)
               
    except subprocess.CalledProcessError as e:
        logger.exception("[%s] error processing [exit code=%d]\n%s", fileid, e.returncode, e.output)
        statusreport['status'] = 'Error processing.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S') 
        statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')
        channel.basic_publish(exchange='',
                routing_key=header.reply_to,
                properties=pika.BasicProperties(correlation_id = \
                                                header.correlation_id),
                body=json.dumps(statusreport)) 
    except:
        logger.exception("[%s] error processing", fileid)
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
            try:
                os.remove(inputfile)
            except OSError as oserror:
                logger.exception("[%s] error removing input file: \n %s", fileid, oserror)

        # Ack
        channel.basic_ack(method.delivery_tag)
        logger.debug("[%s] finished processing", fileid)


if __name__ == "__main__":
    main()
