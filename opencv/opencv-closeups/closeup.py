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
import logging
import time
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


if __name__ == "__main__":
    main()


