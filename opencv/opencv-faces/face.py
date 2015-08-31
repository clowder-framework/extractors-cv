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
import pyclowder.extractors as extractors

def main():
    global extractorName, messageType, rabbitmqExchange, rabbitmqURL    

    #set logging
    logging.basicConfig(format='%(asctime)-15s %(levelname)-7s : %(name)s -  %(message)s', level=logging.WARN)
    logging.getLogger('pyclowder.extractors').setLevel(logging.DEBUG)

    #connect to rabbitmq
    extractors.connect_message_bus(extractorName=extractorName, messageType=messageType, processFileFunction=process_file, 
        rabbitmqExchange=rabbitmqExchange, rabbitmqURL=rabbitmqURL)

 
def process_file(parameters):
    global extractorName, face_cascade_path
    
    inputfile=parameters['inputfile']
    fileid=parameters['fileid']
    
    ext='jpg'

    sectionfile=None
    
    try:
        #extract face from images using opencv face detector
        face_cascade = cv2.CascadeClassifier(face_cascade_path)
        img = cv2.imread(inputfile, cv2.CV_LOAD_IMAGE_GRAYSCALE)
        img_color = cv2.imread(inputfile)
        if img is not None:
            gray = img


            # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            faces=face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=2, minSize=(0, 0), flags=cv2.cv.CV_HAAR_SCALE_IMAGE)
            
            (fd, sectionfile)=tempfile.mkstemp(suffix='.' + ext)
            os.close(fd)

            #To save the section of an image,i.e., faces from the image 
            #for each face detected, create a section corresponding to it and upload section information to server
            #create a preview for the section and upload the preview and its metadata
            for (x,y,w,h) in faces:

                #roi_color = img[y:y+h, x:x+w]
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
                mdata["tags"]=["Human Face Automatically Detected","Person Automatically Detected"]
                mdata["extractor_id"]=extractorName
                extractors.upload_section_tags(sectionid=sectionid, tags=mdata, parameters=parameters)
                
             
            if len(faces)>=1:
                # at least one face was detected. tag file as containing faces
                mdata={}
                mdata["tags"]=["Human Face Automatically Detected","Person Automatically Detected"]
                mdata["extractor_id"]=extractorName                
                extractors.upload_file_tags(tags=mdata, parameters=parameters)

    finally:

        if sectionfile is not None and os.path.isfile(sectionfile):     
            os.remove(sectionfile)  




if __name__ == "__main__":
    main()


