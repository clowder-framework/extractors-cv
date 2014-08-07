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

def main():
    global logger
    global receiver
    # name of receiver
    receiver='ncsa.cv.eyes'

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
 

def findbiggesteye(eyes):
    maxsize=0
    biggesteye=[]
    for (x,y,w,h) in eyes:
        size=w*h
        if size>maxsize:
            maxsize=size
            biggesteye=[x, y, w, h]
    return biggesteye


def create_image_section(inputfile, ext, host, fileid, key):
    global logger
    logger.debug("INSIDE: create_image_section")

    facefile=None
    sectionfile=None

    try:
        #extract face from images using opencv face detector
        face_cascade = cv2.CascadeClassifier('/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt.xml')
        big_eyepair_cascade = cv2.CascadeClassifier('/usr/local/share/OpenCV/haarcascades/haarcascade_mcs_eyepair_big.xml')
        small_eyepair_cascade = cv2.CascadeClassifier('/usr/local/share/OpenCV/haarcascades/haarcascade_mcs_eyepair_small.xml')
        left_eye_cascade=cv2.CascadeClassifier('/usr/local/share/OpenCV/haarcascades/haarcascade_lefteye_2splits.xml')
        right_eye_cascade=cv2.CascadeClassifier('/usr/local/share/OpenCV/haarcascades/haarcascade_righteye_2splits.xml')


        #face_cascade = cv2.CascadeClassifier('/opt/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt.xml')
        #big_eyepair_cascade = cv2.CascadeClassifier('/opt/local/share/OpenCV/haarcascades/haarcascade_mcs_eyepair_big.xml')
        #small_eyepair_cascade = cv2.CascadeClassifier('/opt/local/share/OpenCV/haarcascades/haarcascade_mcs_eyepair_small.xml')
        #left_eye_cascade=cv2.CascadeClassifier('/opt/local/share/OpenCV/haarcascades/haarcascade_lefteye_2splits.xml')
        #right_eye_cascade=cv2.CascadeClassifier('/opt/local/share/OpenCV/haarcascades/haarcascade_righteye_2splits.xml')

        img = cv2.imread(inputfile, cv2.CV_LOAD_IMAGE_GRAYSCALE)
        #img = cv2.imread(inputfile)
        #gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        if img is not None:
            gray = img
            gray = cv2.equalizeHist(gray)
            faces=face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=2, minSize=(0, 0), flags=cv2.cv.CV_HAAR_SCALE_IMAGE)
            logger.debug("Number of faces detected: "+str(len(faces))) 

            faces_all=[]
            eyes_all=[]


            for (x,y,w,h) in faces:
                (fd, facefile)=tempfile.mkstemp(suffix='.' + ext)
                os.close(fd)
                (fd, sectionfile)=tempfile.mkstemp(suffix='.' + ext)
                os.close(fd)

                detected=False
                faces_all.append([x, y, w, h])
                roi_color = img[y:y+h, x:x+w]
                cv2.imwrite(facefile, roi_color)
                roi_gray = gray[y:y+h, x:x+w]
                eyes=big_eyepair_cascade.detectMultiScale(roi_gray, minSize=(0, 0), flags=cv2.cv.CV_HAAR_SCALE_IMAGE)
            #   big_eyes=big_eye_cascade.detectMultiScale(roi_gray, minSize=(w/7, h/7), flags=cv2.cv.CV_HAAR_SCALE_IMAGE)
                if not len(eyes):
                    logger.debug("Trying to detect small eyes")
                    eyes=small_eyepair_cascade.detectMultiScale(roi_gray, minSize=(0, 0), flags=cv2.cv.CV_HAAR_SCALE_IMAGE)
                for (ex,ey,ew,eh) in eyes:
                    eyes_all.append([x+ex, y+ey, ew, eh])
                    roi_eyepair = img[y+ey:y+ey+eh, x+ex:x+ex+ew]
                    cv2.imwrite(sectionfile, roi_eyepair)
                    detected=True
                if not len(eyes):
                    roi_eyes=roi_gray[0:len(roi_gray)/2,:]
                    righteyes=right_eye_cascade.detectMultiScale(roi_eyes, minSize=(0, 0), flags=cv2.cv.CV_HAAR_SCALE_IMAGE)
                    lefteyes=left_eye_cascade.detectMultiScale(roi_eyes, minSize=(0, 0), flags=cv2.cv.CV_HAAR_SCALE_IMAGE)
                    righteye=findbiggesteye(righteyes)
                    lefteye=findbiggesteye(lefteyes)
                    if not len(righteye) and not len(lefteye):
                        continue
                    if not len(righteye):
                        ex=lefteye[0]
                        ey=lefteye[1]
                        ew=lefteye[2]
                        eh=lefteye[3]
                    elif not len(lefteye):
                        ex=righteye[0]
                        ey=righteye[1]
                        ew=righteye[2]
                        eh=righteye[3]
                    else:
                        ex = min(righteye[0], lefteye[0])       
                        ey = min(righteye[1], lefteye[1])
                        ew = max(righteye[0]+righteye[2], lefteye[0]+lefteye[2])-ex
                        eh = max(righteye[1]+righteye[3], lefteye[1]+lefteye[3])-ey
                    eyes_all.append([x+ex, y+ey, ew, eh])
                    roi_eyepair = img[y+ey:y+ey+eh, x+ex:x+ex+ew]
                    cv2.imwrite(sectionfile, roi_eyepair)
                    detected=True
         
                # create section of an image
                if detected:
                    url=host + 'api/sections?key=' + key
                    logger.debug("url=%s",url)
                    secdata={}
                    secdata["file_id"]=fileid
                    #print(type(fileid),type(x),type(y),type(w),type(h))
                    secdata["area"]={"x":int(ex), "y":int(ey),"w":int(ew),"h":int(eh)}
                    
                    #logger.debug("section json [%s]",(json.dumps(secdata)))
                    
                    headers={'Content-Type': 'application/json'}
                   
                    r = requests.post(url,headers=headers, data=json.dumps(secdata))
                    r.raise_for_status()
                    
                    sectionid=r.json()['id']
                    logger.debug(("section id [%s]",sectionid))

                    url=host + 'api/previews?key=' + key
                    # upload preview image
                    with open(sectionfile, 'rb') as f:
                        files={"File" : f}
                        rc = requests.post(url, files=files)
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
                    rp = requests.post(url, headers=headers, data=json.dumps(imgdata));
                    rp.raise_for_status()
                    

                    url=host+'api/sections/'+ sectionid+'/tags?key=' + key
                    mdata={}
                    mdata["tags"]=["Human Eyes Automatically Detected"]
                    mdata["extractor_id"]=receiver
                    logger.debug("tags: %s",json.dumps(mdata))
                    rt = requests.post(url, headers=headers, data=json.dumps(mdata))
                    rt.raise_for_status()
                    logger.debug("[%s] created section and previews of type %s", fileid, ext)

                    
                    url=host+'api/files/'+ fileid+'/tags?key=' + key
                    mdata={}
                    mdata["tags"]=["Human Eyes Automatically Detected"]
                    mdata["extractor_id"]=receiver
                    logger.debug("tags: %s",json.dumps(mdata))
                    rtf = requests.post(url, headers=headers, data=json.dumps(mdata))
                    rtf.raise_for_status()
                    logger.debug("[%s] created section and previews of type %s", fileid, ext)

    finally:
        if sectionfile is not None and os.path.isfile(sectionfile):     
            os.remove(sectionfile) 
        if facefile is not None and os.path.isfile(facefile):
            os.remove(facefile)  


def get_image_data(imagefile):
    global logger

    text=subprocess.check_output(['identify', imagefile], stderr=subprocess.STDOUT)
    return text

def on_message(channel, method, header, body):
    global logger, receiver
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
        r=requests.get(url, stream=True)
        r.raise_for_status()
        (fd, inputfile)=tempfile.mkstemp()
        with os.fdopen(fd, "w") as f:
            for chunk in r.iter_content(chunk_size=10*1024):
                f.write(chunk)

        
        statusreport['status'] = 'Extracting eyes from image and creating sections.'
        statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        statusreport['end'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        channel.basic_publish(exchange='',
                            routing_key=header.reply_to,
                            properties=pika.BasicProperties(correlation_id = \
                                                        header.correlation_id),
                            body=json.dumps(statusreport))

        # create previews
        #create_image_preview(inputfile, 'jpg', '800x600>', host, fileid, key)
        create_image_section(inputfile, 'jpg', host, fileid, key)
        #create_image_preview(inputfile, 'jpg', '800x600>', host, fileid, key, '-rotate', '90')
        #create_image_preview(inputfile, 'jpg', '800x600>', host, fileid, key, '-rotate', '180')
        #create_image_preview(inputfile, 'jpg', '800x600>', host, fileid, key, '-rotate', '270')
        

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
