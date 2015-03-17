#!/usr/bin/env python
import pika
import requests
import sys
import logging
import time
import json
import subprocess
import tempfile
import os
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
    global extractorName, pdfimagespath
    
    inputfile=parameters['inputfile']

    try:

        (dirname, filename) = os.path.split(inputfile)
        basename = filename+"-image"
        basefolder=os.path.dirname(os.path.realpath(__file__))

        # call actual program
        output = subprocess.check_output([pdfimagespath, '-j', '-p', inputfile, basename], stderr=subprocess.STDOUT);

        # upload each of the images extracted
        generated_files = []
        for f in os.listdir(basefolder):
            if f.startswith(basename):
                p = os.path.join(basefolder,f)
                # upload the file to the dataset
                new_fid=extractors.upload_file_to_dataset(filepath=p, parameters=parameters)
                new_url=extractors.get_file_URL(fileid=new_fid, parameters=parameters)
                generated_files.append(new_url)

                if p is not None and os.path.isfile(p):
                    os.remove(p)

        if generated_files:
            mdata = {}
            mdata["extractor_id"]=extractorName
            mdata["generated_files"]=generated_files
            extractors.upload_file_metadata(mdata=mdata, parameters=parameters)


    finally:
        if p is not None and os.path.isfile(p):
            os.remove(p)



if __name__ == "__main__":
    main()