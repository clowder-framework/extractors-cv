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

    # name of receiver
    global receiver
    receiver='ncsa.cv.face'

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
 
def create_image_section(inputfile, ext, host, fileid, key):
    global logger, receiver, sslVerify
    logger.debug("INSIDE: create_image_section")
    
    sectionfile=None
    
    try:
        #extract face from images using opencv face detector
        #face_cascade = cv2.CascadeClassifier('/opt/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt.xml')
        face_cascade = cv2.CascadeClassifier('/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt.xml')
        img = cv2.imread(inputfile, cv2.CV_LOAD_IMAGE_GRAYSCALE)
        
        if img is not None:
            gray = img


            # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            faces=face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=2, minSize=(0, 0), flags=cv2.cv.CV_HAAR_SCALE_IMAGE)
            
            logger.debug("Number of faces detected: "+str(len(faces))) 

            #To save the section of an image,i.e., faces from the image 
            #for each face detected, create a section corresponding to it and upload section information to server
            #create a preview for the section and upload the preview and its metadata
            for (x,y,w,h) in faces:
                roi_color = img[y:y+h, x:x+w]
                (fd, sectionfile)=tempfile.mkstemp(suffix='.' + ext)
                os.close(fd)
                      
                cv2.imwrite(sectionfile, roi_color)
                

                # create section of an image
                
                url=host + 'api/sections?key=' + key
                logger.debug("url=%s",url)
                secdata={}
                secdata["file_id"]=fileid
                #print(type(fileid),type(x),type(y),type(w),type(h))
                secdata["area"]={"x":int(x), "y":int(y),"w":int(w),"h":int(h)}
                
                #logger.debug("section json [%s]",(json.dumps(secdata)))
                
                headers={'Content-Type': 'application/json'}
               
                r = requests.post(url,headers=headers, data=json.dumps(secdata), verify=sslVerify)
                r.raise_for_status()
                
                sectionid=r.json()['id']
                logger.debug(("section id [%s]",sectionid))

                url=host + 'api/previews?key=' + key
                # upload preview image
                with open(sectionfile, 'rb') as f:
                    files={"File" : f}
                    rc = requests.post(url, files=files, verify=sslVerify)
                    rc.raise_for_status()
                previewid = rc.json()['id']
                logger.debug("preview id=[%s]",rc.json()['id'])

                # associate uploaded image with section
                imgdata={}
                imgdata['section_id']=sectionid
                imgdata['width']=str(w)
                imgdata['height']=str(h)
                imgdata['extractor_id']=receiver
            
                headers={'Content-Type': 'application/json'}
                url = host + 'api/previews/' + previewid + '/metadata?key=' + key
                # url=host + 'api/files/' + fileid + '/previews/' + previewid + '?key=' + key
                rp = requests.post(url, headers=headers, data=json.dumps(imgdata), verify=sslVerify);
                rp.raise_for_status()

                
                
                url=host+'api/sections/'+ sectionid+'/tags?key=' + key
                mdata={}
                mdata["tags"]=["Human Face Automatically Detected","Person Automatically Detected"]
                mdata["extractor_id"]=receiver
                logger.debug("tags: %s",json.dumps(mdata))
                rt = requests.post(url, headers=headers, data=json.dumps(mdata), verify=sslVerify)
                rt.raise_for_status()
            if len(faces)>=1:
                url=host+'api/files/'+ fileid+'/tags?key=' + key
                mdata={}
                mdata["tags"]=["Human Face Automatically Detected","Person Automatically Detected"]
                mdata["extractor_id"]=receiver
                logger.debug("tags: %s",json.dumps(mdata))
                rtf = requests.post(url, headers=headers, data=json.dumps(mdata), verify=sslVerify)
                rtf.raise_for_status()
                logger.debug("[%s] created section and previews of type %s", fileid, ext)
    finally:
        #os.remove(previewfile)
        if sectionfile is not None and os.path.isfile(sectionfile):     
            os.remove(sectionfile)  
def get_image_data(imagefile):
    global logger

    text=subprocess.check_output(['identify', imagefile], stderr=subprocess.STDOUT)
    return text

def on_message(channel, method, header, body):
    global logger, receiver, sslVerify
    statusreport = {}

    inputfile=None
    try:
        # parse body back from json
        jbody=json.loads(body)
        key=jbody['secretKey']
        host=jbody['host']
        #logger.debug("host[%s]=",host)
        fileid=jbody['id']
        intermediatefileid=jbody['intermediateId']
        if not (host.endswith('/')):
            host += '/'

        # print what we are doing
        logger.debug("[%s] started processing", fileid)
        # for status reports
        statusreport['file_id'] = fileid
        statusreport['extractor_id'] = receiver

        # fetch data

        statusreport['status'] = 'Downloading image file.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')
        channel.basic_publish(exchange='',
                            routing_key=header.reply_to,
                            properties=pika.BasicProperties(correlation_id = \
                                                        header.correlation_id),
                            body=json.dumps(statusreport)) 

        url=host + 'api/files/' + fileid + '?key=' + key
        print  url
        r=requests.get(url, stream=True, verify=sslVerify)
        r.raise_for_status()

        (fd, inputfile)=tempfile.mkstemp()
        with os.fdopen(fd, "w") as f:
            for chunk in r.iter_content(chunk_size=10*1024):
                f.write(chunk)

        
        statusreport['status'] = 'Extracting face from image and creating a section.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')
        channel.basic_publish(exchange='',
                            routing_key=header.reply_to,
                            properties=pika.BasicProperties(correlation_id = \
                                                        header.correlation_id),
                            body=json.dumps(statusreport))

        # create previews
        #create_image_preview(inputfile, 'jpg', '800x600>', host, fileid, key)
        create_image_section(inputfile, 'jpg', host, fileid, key)
               
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
        statusreport['end'] = time.strftime('%Y-%m-%dT%H:%M:%S')
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
