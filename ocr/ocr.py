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
import logging
import time
import uuid
from config import *
import pyclowder.extractors as extractors

def main():
    global extractorName, messageType, rabbitmqExchange, rabbitmqURL, logger

    #set logging
    logging.basicConfig(format='%(asctime)-15s %(levelname)-7s : %(name)s -  %(message)s', level=logging.WARN)
    logging.getLogger('pyclowder.extractors').setLevel(logging.INFO)
    logger = logging.getLogger('ocr')
    logger.setLevel(logging.DEBUG)

    register_extractor(clowderUrl, apiKey)

    #connect to rabbitmq
    extractors.connect_message_bus(extractorName=extractorName, messageType=messageType, processFileFunction=process_file, 
        rabbitmqExchange=rabbitmqExchange, rabbitmqURL=rabbitmqURL)
 

def ocr(filename, tmpfilename):
    text=""
    tmpfile=None
    try:
        subprocess.check_call(["tesseract", filename, tmpfilename])
        tmpfile="./"+tmpfilename+".txt"
        with open(tmpfile, 'r') as f:
            text = f.read()
    finally:
        if tmpfile is not None and os.path.isfile(tmpfile):
            os.remove(tmpfile)
        return clean_text(text)

def clean_text(text):
    t = ""
    words=text.split()
    for word in words:
        w = clean_word(word) 
        if w != "":
            t+= w + " "
    return t

def clean_word(word):
    cw = word.strip('(){}[].,')
    if cw.isalnum() and len(cw)>=2:
        return cw
    else:
        return ""


def process_file(parameters):
    global extractorName
    
    inputfile=parameters['inputfile']
    
    ocrtext = ocr(inputfile, str(uuid.uuid4()))
    mdata={}
    mdata["extractor_id"]=extractorName
    mdata["ocr_simple"]=[ocrtext]

    extractors.upload_file_metadata(mdata=mdata, parameters=parameters)

def register_extractor(host, key):
    """Register extractor info with Clowder"""

    logger.info("Registering extractor using key " + key)

    headers = {'Content-Type': 'application/json'}

    if not host.endswith("/"):
        host += "/"

    url = host+'api/extractors?key=' + key

    info = {
        "@context": "",
        "name": extractorName,
        "version": "1.0",
        "description": "Simple OCR (Optical Character Recognition) extractor to extract text from an image",
        "author": "Liana Diesendruck <ldiesend@illinois.edu>",
        "contributors": ["Rob Kooper <kooper@illinois.edu>", "Rui Liu <ruiliu@illinois.edu>"],
        "repository": {"repType": "git", "repUrl": "https://opensource.ncsa.illinois.edu/bitbucket/scm/cats/extractors-cv.git"},
        "dependencies": ["tesseract"]
    }

    r = requests.post(url, headers=headers, data=json.dumps(info), verify=sslVerify)
    print "Response: ", r.text
    return r.raise_for_status()

if __name__ == "__main__":
    main()
