#!/usr/bin/env python

import tempfile
import subprocess
import os
import time
import logging
import json
from config import *
import pyclowder.extractors as extractors

def main():
    global extractorName, messageType, rabbitmqExchange, rabbitmqURL, logger
    global matlab_process

    matlab_process = None

    #set logging
    logging.basicConfig(format='%(levelname)-7s : %(name)s -  %(message)s', level=logging.WARN)
    logging.getLogger('pyclowder.extractors').setLevel(logging.INFO)
    logger = logging.getLogger('extractor')
    logger.setLevel(logging.DEBUG)

    # setup
    extractors.setup(extractorName=extractorName,
                     messageType=messageType,
                     rabbitmqURL=rabbitmqURL,
                     rabbitmqExchange=rabbitmqExchange)

    extractors.register_extractor(registrationEndpoints)

    #connect to rabbitmq
    extractors.connect_message_bus(extractorName=extractorName, 
                                   messageType=messageType, 
                                   processFileFunction=process_file, 
                                   rabbitmqExchange=rabbitmqExchange, 
                                   rabbitmqURL=rabbitmqURL,
                                   checkMessageFunction=None)

    # kill matlab
    if matlab_process and not matlab_process.poll():
        matlab_process.stdin.write("quit()\n")
        matlab_process.kill()

def process_file(parameters):
    global extractorName
    
    inputfile=parameters['inputfile']
    tmpfile=inputfile+".txt"

    try:
        run_classify(inputfile, tmpfile)

        #tmpfile resulting from running the matlab code should contain two lines. 1st = category, 2nd = score
        f = open(tmpfile, 'r')
        category = f.readline().strip('\n')
        score = f.readline().strip('\n')
        f.close()

        # context url
        context_url = 'https://clowder.ncsa.illinois.edu/contexts/metadata.jsonld'

        # store results as metadata
        metadata = {
                '@context': [context_url, 
                    {'basic_caltech101_category': 'http://clowder.ncsa.illinois.edu/clowder/api/extractors/ncsa.cv.caltech101#basic_caltech101_category',
                     'basic_caltech101_score': 'http://clowder.ncsa.illinois.edu/clowder/api/extractors/ncsa.cv.caltech101#basic_caltech101_score'}
                ],
                'attachedTo': {'resourceType': 'file', 'id': parameters["fileid"]},
                'agent': {
                    '@type': 'cat:extractor',
                    'extractor_id': 'https://clowder.ncsa.illinois.edu/clowder/api/extractors/ncsa.cv.caltech101'
                },
                'content': {'basic_caltech101_category': category,
                            'basic_caltech101_score': score}
                }

        extractors.upload_file_metadata_jsonld(mdata=metadata, parameters=parameters)

    finally:
        if os.path.isfile(tmpfile):
            os.remove(tmpfile)


def run_classify(inputfile, outputfile):
    global matlab_process, matlabBinary

    if not matlab_process or matlab_process.poll():
        folder = os.path.dirname(os.path.realpath(__file__))
        args = [matlabBinary, '-nodisplay', '-nosplash']
        matlab_process = subprocess.Popen(args, stdin=subprocess.PIPE, shell=True)
        matlab_process.stdin.write("cd '" + folder + "';\n")
        matlab_process.stdin.write("run('./vlfeat/toolbox/vl_setup');\n")
        matlab_process.stdin.write("cd('./vlfeat/apps/');\n")
        matlab_process.stdin.write("load('./data/baseline-model.mat');\n")
        matlab_process.stdin.write("cd '" + folder + "';\n")

    matlab_process.stdin.write("image = imread('" + inputfile + "');\n")
    matlab_process.stdin.write("[label, score] = model.classify(model, image);\n")
    matlab_process.stdin.write("fileID = fopen('" + outputfile + "','w');\n")
    matlab_process.stdin.write("fprintf(fileID,'%s\\n', label);\n")
    matlab_process.stdin.write("fprintf(fileID,'%f\\n', score);\n")
    matlab_process.stdin.write("fclose(fileID);\n")

    while not os.path.isfile(outputfile) and not matlab_process.poll():
        time.sleep(0.1)


if __name__ == "__main__":
    main()
