#!/usr/bin/env python
import pika
import sys
import json
import traceback
import requests
import tempfile
import subprocess
from subprocess import Popen, PIPE
import os
import itertools
import logging
import time
from config import *
import pymedici.extractors as extractors



def main():
    global extractorName, messageType, rabbitmqExchange, rabbitmqURL    
    global matlab_process

    install_folder=os.path.dirname(os.path.realpath(__file__))
    # open matlab, go to required directory, and keep it running
    matlab_process = subprocess.Popen(['matlab', '-nodesktop', '-noFigureWindows', '-nosplash', '-r'], stdin=PIPE, stdout=PIPE, shell=True); #-nodisplay
    cd_command="cd '"+install_folder+"'\n"
    matlab_process.stdin.write(cd_command)
    matlab_process.stdin.flush()
    time.sleep(1) 
    # setup vlfeat
    matlab_process.stdin.write("run('./vlfeat/toolbox/vl_setup');\n")
    matlab_process.stdin.flush()
    time.sleep(5) 
    # defines model as a global matlab variable
    matlab_process.stdin.write("global model\n")
    matlab_process.stdin.flush()
    time.sleep(1) 
    # load pre-trained classifier into model
    matlab_process.stdin.write("cd('./vlfeat/apps/');\n")
    matlab_process.stdin.flush()
    time.sleep(1) 
    matlab_process.stdin.write("load('./data/baseline-model.mat');\n")
    matlab_process.stdin.flush()
    time.sleep(1)
    #go back to the original directory to be able to call the matlab classify function
    matlab_process.stdin.write(cd_command)
    matlab_process.stdin.flush()
    time.sleep(1) 


    #set logging
    logging.basicConfig(format='%(levelname)-7s : %(name)s -  %(message)s', level=logging.WARN)
    logging.getLogger('pymedici.extractors').setLevel(logging.INFO)

    #connect to rabbitmq
    extractors.connect_message_bus(extractorName=extractorName, messageType=messageType, processFileFunction=process_file, 
        rabbitmqExchange=rabbitmqExchange, rabbitmqURL=rabbitmqURL)
 

    # kill matlab
    matlab_process.stdin.write("quit()\n")
    matlab_process.stdin.flush()
    matlab_process.kill()


def process_file(parameters):
    global extractorName
    global matlab_process
    
    inputfile=parameters['inputfile']
    tmpfile=inputfile+".txt"

    try:
        # call matlab code to classify image
        extract_command = "classify('"+inputfile+"', '"+tmpfile+"')\n"
        matlab_process.stdin.write(extract_command)
        matlab_process.stdin.flush()

        #wait for result file (tmpfile) to be created
        while (not os.path.isfile(tmpfile)):
            time.sleep(0.1)

        #tmpfile resulting from running the matlab code should contain two lines. 1st = category, 2nd = score
        f = open(tmpfile, 'r')
        category = f.readline().strip('\n')
        score = f.readline().strip('\n')
        f.close()

        mdata={}
        mdata["extractor_id"]=extractorName
        mdata["basic_caltech101_category"]=[category]
        mdata["basic_caltech101_score"]=[score]

        extractors.upload_file_metadata(mdata=mdata, parameters=parameters)

    finally:
        if os.path.isfile(tmpfile):
            os.remove(tmpfile)


if __name__ == "__main__":
    main()


