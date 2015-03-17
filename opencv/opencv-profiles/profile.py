#!/usr/bin/env python
import pika
import sys
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
import logging
from config import *
import pymedici.extractors as extractors

def main():
    global extractorName, messageType, rabbitmqExchange, rabbitmqURL    

    #set logging
    logging.basicConfig(format='%(levelname)-7s : %(name)s -  %(message)s', level=logging.WARN)
    logging.getLogger('pymedici.extractors').setLevel(logging.INFO)

    #connect to rabbitmq
    extractors.connect_message_bus(extractorName=extractorName, messageType=messageType, processFileFunction=process_file, 
        rabbitmqExchange=rabbitmqExchange, rabbitmqURL=rabbitmqURL)

 
def process_file(parameters):
    global extractorName, profileface_cascade_path
    
    inputfile=parameters['inputfile']
    fileid=parameters['fileid']
    
    ext='jpg'

    sectionfile=None
    
    try:

        profile_face_cascade = cv2.CascadeClassifier(profileface_cascade_path)

        img = cv2.imread(inputfile, cv2.CV_LOAD_IMAGE_GRAYSCALE)
        img_color = cv2.imread(inputfile)
        
        #gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if img is not None:
            gray = img
            gray = cv2.equalizeHist(gray)

            faces=profile_face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=10)

            (fd, sectionfile)=tempfile.mkstemp(suffix='.' + ext)
            os.close(fd)

            for (x,y,w,h) in faces:
                roi_color = img_color[y:y+h, x:x+w]
                cv2.imwrite(sectionfile, roi_color)

                # create section of an image, add to sections mongo collection                                
                secdata={}
                secdata["file_id"]=fileid
                secdata["area"]={"x":int(x), "y":int(y),"w":int(w),"h":int(h)}         

                #upload section to medici
                sectionid=extractors.upload_section(sectiondata=secdata, parameters=parameters)


                # section preview image metadata
                imgdata={}
                imgdata['section_id']=sectionid
                imgdata['width']=str(w)
                imgdata['height']=str(h)
                imgdata['extractor_id']=extractorName

                #upload face as a section preview and associate metadata
                extractors.upload_preview(previewfile=sectionfile, previewdata=imgdata, parameters=parameters)


                # add tags to the created section
                mdata={}
                mdata["tags"]=["Human Profile Automatically Detected"]
                mdata["extractor_id"]=extractorName
                extractors.upload_section_tags(sectionid=sectionid, tags=mdata, parameters=parameters)

                             
            if len(faces)>=1:
                # at least one profile was detected. tag file as containing profiles
                mdata={}
                mdata["tags"]=["Human Profile Automatically Detected"]
                mdata["extractor_id"]=extractorName                
                extractors.upload_file_tags(tags=mdata, parameters=parameters)

    finally:
        #os.remove(previewfile)
        if sectionfile is not None and os.path.isfile(sectionfile):     
            os.remove(sectionfile)  




if __name__ == "__main__":
    main()


