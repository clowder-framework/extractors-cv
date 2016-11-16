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

    try:
        register_extractor(registrationEndpoints)
    except Exception as e:
        logger.warn('Error in registering extractor: ' + str(e))

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

    ocrtext = ocr(inputfile, str(uuid.uuid4())).strip()
    if not ocrtext:
        ocrtext = 'No text detected'

    # context url
    context_url = 'https://clowder.ncsa.illinois.edu/contexts/metadata.jsonld'

    # store results as metadata
    metadata = {
        '@context': [context_url, 
                     {'ocr_text': 'http://clowder.ncsa.illinois.edu/' + extractorName + '#ocr_text'}],
        'attachedTo': {'resourceType': 'file', 'id': parameters["fileid"]},
        'agent': {'@type': 'cat:extractor',
                  'extractor_id': 'https://clowder.ncsa.illinois.edu/clowder/api/extractors/' + extractorName},
        'content': {'ocr_text': ocrtext}
    }

    # upload metadata
    extractors.upload_file_metadata_jsonld(mdata=metadata, parameters=parameters)

    logger.info("Uploaded metadata %s", metadata)

def register_extractor(registrationEndpoints):
    """Register extractor info with Clowder"""

    logger.info("Registering extractor...")
    headers = {'Content-Type': 'application/json'}
    with open('extractor_info.json') as info_file:
        info = json.load(info_file)
        info["name"] = extractorName
        for url in registrationEndpoints.split(','):
            r = requests.post(url.strip(), headers=headers, data=json.dumps(info), verify=sslVerify)
            print "Response: ", r.text


if __name__ == "__main__":
    main()
