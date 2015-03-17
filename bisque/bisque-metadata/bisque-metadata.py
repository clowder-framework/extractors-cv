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
import xmltodict
from xml.dom.minidom import parse, parseString
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


def call_bisque(filename):
    global bisqueUser
    global bisquePassword
    global bisqueServer
    
    metadict ={}
    posturl = bisqueServer+'/import/transfer'
    files = {'file': open(filename, 'rb')}
    r = requests.post(posturl, files=files , auth=(bisqueUser, bisquePassword))

    if(r.status_code==200):
        xmldoc = parseString(r.text)
        imagelist =  xmldoc.getElementsByTagName('image')
        imageuri = imagelist[0].attributes['uri'].value
        imageuniq = imagelist[0].attributes['resource_uniq'].value


        r = requests.get(bisqueServer+'/image_service/'+imageuniq+'?meta', auth=(bisqueUser, bisquePassword))

        metadict = xmltodict.parse(r.text) #dict containing xml fields
        # metajson = json.dumps(metadict) #json object

        r = requests.delete(imageuri, auth=(bisqueUser, bisquePassword))

    return metadict['resource']#metadict
    
    
def process_file(parameters):
    global extractorName
    
    inputfile=parameters['inputfile']
    
    bisquedict = call_bisque(inputfile)

    mdata={}
    mdata["bisque_metadata"]=[bisquedict]
    mdata["extractor_id"]=extractorName
    #upload metadata
    extractors.upload_file_metadata(mdata=mdata, parameters=parameters)

        

if __name__ == "__main__":
    main()
