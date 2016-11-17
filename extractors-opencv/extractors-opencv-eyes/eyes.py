#!/usr/bin/env python

import json
import requests
import tempfile
import os
import cv2
import logging
from config import *
import pyclowder.extractors as extractors

def main():
    global extractorName, messageType, rabbitmqExchange, rabbitmqURL, logger

    #set logging
    logging.basicConfig(format='%(asctime)-15s %(levelname)-7s : %(name)s -  %(message)s', level=logging.WARN)
    logging.getLogger('pyclowder.extractors').setLevel(logging.DEBUG)
    logger = logging.getLogger('eyes')
    logger.setLevel(logging.DEBUG)

    extractors.setup(extractorName, messageType, rabbitmqExchange, rabbitmqURL, sslVerify)
    extractors.register_extractor(registrationEndpoints)

    #connect to rabbitmq
    extractors.connect_message_bus(extractorName=extractorName, messageType=messageType, processFileFunction=process_file, 
        rabbitmqExchange=rabbitmqExchange, rabbitmqURL=rabbitmqURL)


def findbiggesteye(eyes):
    maxsize=0
    biggesteye=[]
    for (x,y,w,h) in eyes:
        size=w*h
        if size>maxsize:
            maxsize=size
            biggesteye=[x, y, w, h]
    return biggesteye

 
def process_file(parameters):
    global face_cascade_path, big_eyepair_cascade_path, small_eyepair_cascade_path, left_eye_cascade_path, right_eye_cascade_path
    global extractorName
    

    inputfile=parameters['inputfile']
    fileid=parameters['fileid']
    
    ext='jpg'

    sectionfile=None

    
    try:
        face_cascade = cv2.CascadeClassifier(face_cascade_path)
        big_eyepair_cascade = cv2.CascadeClassifier(big_eyepair_cascade_path)
        small_eyepair_cascade = cv2.CascadeClassifier(small_eyepair_cascade_path)
        left_eye_cascade=cv2.CascadeClassifier(left_eye_cascade_path)
        right_eye_cascade=cv2.CascadeClassifier(right_eye_cascade_path)

        img = cv2.imread(inputfile, cv2.CV_LOAD_IMAGE_GRAYSCALE)
        img_color = cv2.imread(inputfile)

        if img is not None:
            gray = img
            gray = cv2.equalizeHist(gray)
            faces=face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=2, minSize=(0, 0), flags=cv2.cv.CV_HAAR_SCALE_IMAGE)

            faces_all=[]
            eyes_all=[]

            (fd, sectionfile)=tempfile.mkstemp(suffix='.' + ext)
            os.close(fd)

            positions=[]
            for (x,y,w,h) in faces:
                detected=False
                faces_all.append([x, y, w, h])
                roi_color = img_color[y:y+h, x:x+w]
                cv2.imwrite(sectionfile, roi_color)
                roi_gray = gray[y:y+h, x:x+w]
                eyes=big_eyepair_cascade.detectMultiScale(roi_gray, minSize=(0, 0), flags=cv2.cv.CV_HAAR_SCALE_IMAGE)
            #   big_eyes=big_eye_cascade.detectMultiScale(roi_gray, minSize=(w/7, h/7), flags=cv2.cv.CV_HAAR_SCALE_IMAGE)
                if not len(eyes):
                    eyes=small_eyepair_cascade.detectMultiScale(roi_gray, minSize=(0, 0), flags=cv2.cv.CV_HAAR_SCALE_IMAGE)
                for (ex,ey,ew,eh) in eyes:
                    eyes_all.append([x+ex, y+ey, ew, eh])
                    roi_eyepair = img_color[y+ey:y+ey+eh, x+ex:x+ex+ew]
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
                    roi_eyepair = img_color[y+ey:y+ey+eh, x+ex:x+ex+ew]
                    cv2.imwrite(sectionfile, roi_eyepair)
                    detected=True
         
                # create section of an image
                if detected:

                    # create section of the image                           
                    secdata={}
                    secdata["file_id"]=fileid
                    secdata["area"]={"x":int(ex), "y":int(ey),"w":int(ew),"h":int(eh)}

                    #upload section to medici
                    sectionid=extractors.upload_section(sectiondata=secdata, parameters=parameters)


                    # section preview image metadata
                    imgdata={}
                    imgdata['section_id']=sectionid
                    imgdata['width']=str(ew)
                    imgdata['height']=str(eh)
                    imgdata['extractor_id']=extractorName

                    pos_md={}
                    pos_md['section_id']=sectionid
                    pos_md['x']=str(x)
                    pos_md['y']=str(y)
                    pos_md['width']=str(w)
                    pos_md['height']=str(h)
                    positions.append(pos_md)

                    #upload eyes as a section preview and associate metadata
                    extractors.upload_preview(previewfile=sectionfile, previewdata=imgdata, parameters=parameters)


                    # add tags to the created section
                    mdata={}
                    mdata["tags"]=["Human Eyes Automatically Detected"]
                    mdata["extractor_id"]=extractorName
                    extractors.upload_section_tags(sectionid=sectionid, tags=mdata, parameters=parameters)

                
                    # at least one face was detected. tag file as containing faces
                    mdata={}
                    mdata["tags"]=["Human Eyes Automatically Detected"]
                    mdata["extractor_id"]=extractorName                
                    extractors.upload_file_tags(tags=mdata, parameters=parameters)

                    # Add metadata if at least one eye was detected.
                    # context url
                    context_url = 'https://clowder.ncsa.illinois.edu/contexts/metadata.jsonld'

                    # store results as metadata
                    metadata = {
                        '@context': [context_url, 
                                     {'eyes': 'http://clowder.ncsa.illinois.edu/' + extractorName + '#eyes'}],
                        'attachedTo': {'resourceType': 'file', 'id': parameters["fileid"]},
                        'agent': {'@type': 'cat:extractor',
                                  'extractor_id': 'https://clowder.ncsa.illinois.edu/clowder/api/extractors/' + extractorName},
                        'content': {'eyes': positions}
                    }

                    # upload metadata
                    extractors.upload_file_metadata_jsonld(mdata=metadata, parameters=parameters)
                    logger.info("Uploaded metadata %s", metadata)

    finally:

        if sectionfile is not None and os.path.isfile(sectionfile):     
            os.remove(sectionfile)  

if __name__ == "__main__":
    main()
