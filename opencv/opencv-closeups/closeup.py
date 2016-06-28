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
    logger = logging.getLogger('closeups')
    logger.setLevel(logging.DEBUG)

    extractors.setup(extractorName, messageType, rabbitmqExchange, rabbitmqURL, sslVerify)
    extractors.register_extractor(registrationEndpoints)

    #connect to rabbitmq
    extractors.connect_message_bus(extractorName=extractorName, messageType=messageType, processFileFunction=process_file, 
        rabbitmqExchange=rabbitmqExchange, rabbitmqURL=rabbitmqURL)

def process_file(parameters):
    global extractorName, face_cascade_path, profileface_cascade_path
    
    inputfile=parameters['inputfile']
    fileid=parameters['fileid']
        

    face_cascade = cv2.CascadeClassifier(face_cascade_path)
    profile_face_cascade = cv2.CascadeClassifier(profileface_cascade_path)
           
    img = cv2.imread(inputfile, cv2.CV_LOAD_IMAGE_GRAYSCALE)

    if img is not None:
        gray=img
        gray = cv2.equalizeHist(gray)
        
        imgh=len(gray)
        imgw=len(gray[0])
    
        midCloseUp=False
        fullCloseUp=False

        closeupSet = set()
        faces=face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=2, minSize=(imgw/8, imgh/8), flags=cv2.cv.CV_HAAR_SCALE_IMAGE)
        for (x,y,w,h) in faces:
            if ((w*h>=(imgw*imgh/3)) or (w>=0.8*imgw and h>=0.5*imgh) or (w>=0.5*imgw and h>=0.8*imgh)): #this is a closeup
                fullCloseUp=True
                closeupSet.add((x,y,w,h))
        for (x,y,w,h) in faces: 
            if(w*h>=(imgw*imgh/8)): #this is a medium closeup
                midCloseUp=True
                closeupSet.add((x,y,w,h))
        
        profilefaces=profile_face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=10, minSize=(imgw/8, imgh/8))
        for (x,y,w,h) in profilefaces:
            if ((w*h>=(imgw*imgh/3)) or (w>=0.8*imgw and h>=0.5*imgh) or (w>=0.5*imgw and h>=0.8*imgh)): #this is a closeup
                fullCloseUp=True
                closeupSet.add((x,y,w,h))
        for (x,y,w,h) in profilefaces: 
            if(w*h>=(imgw*imgh/8)): #this is a medium closeup
                midCloseUp=True
                closeupSet.add((x,y,w,h))

        if fullCloseUp:
            mdata={}
            mdata["tags"]=["Full Close Up Automatically Detected"]
            mdata["extractor_id"]=extractorName
            extractors.upload_file_tags(tags=mdata, parameters=parameters)

        elif midCloseUp:
            mdata={}
            mdata["tags"]=["Mid Close Up Automatically Detected"]
            mdata["extractor_id"]=extractorName
            extractors.upload_file_tags(tags=mdata, parameters=parameters)

        positions=[]
        # Add metadata if at least one closeup was detected.
        if len(closeupSet) >= 1:
            for (x,y,w,h) in closeupSet:
                pos_md={}
                pos_md['x']=str(x)
                pos_md['y']=str(y)
                pos_md['width']=str(w)
                pos_md['height']=str(h)
                positions.append(pos_md)

            # context url
            context_url = 'https://clowder.ncsa.illinois.edu/clowder/contexts/metadata.jsonld'

            # store results as metadata
            metadata = {
                '@context': [context_url, 
                             {'closeups': 'http://clowder.ncsa.illinois.edu/' + extractorName + '#closeups'}],
                'attachedTo': {'resourceType': 'file', 'id': parameters["fileid"]},
                'agent': {'@type': 'cat:extractor',
                          'extractor_id': 'https://clowder.ncsa.illinois.edu/clowder/api/extractors/' + extractorName},
                'content': {'closeups': positions}
            }

            # upload metadata
            extractors.upload_file_metadata_jsonld(mdata=metadata, parameters=parameters)
            logger.info("Uploaded metadata %s", metadata)


if __name__ == "__main__":
    main()


