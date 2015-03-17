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
import zipfile
import os.path
import shutil
import csv
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
    global extractorName
    
    inputfile=parameters['inputfile']
    datasetid=parameters['datasetId']
    
    try:
       
        basefolder=os.path.dirname(os.path.realpath(__file__))
        pipelinepath=os.path.join(basefolder, "ExampleFly.cp")
        datasetinputfolder=os.path.join(basefolder, datasetid+"_fly_input")
        datasetoutputfolder=os.path.join(basefolder, datasetid+"_fly_output")
        
        zfile = zipfile.ZipFile(inputfile)
        if not os.path.exists(datasetinputfolder):
            os.makedirs(datasetinputfolder)
        if not os.path.exists(datasetoutputfolder):
            os.makedirs(datasetoutputfolder)
        
        
        dird = ""
        dirf = ""
        dirr = ""
        countd = 0
        countf = 0
        countr = 0
        for name in zfile.namelist():
            (dirname, filename) = os.path.split(name)

            if (filename.find("D.TIF")!=-1 or filename.find("F.TIF")!=-1 or filename.find("R.TIF")!=-1) and not filename.startswith("."):
                dirname=os.path.join(datasetinputfolder, dirname)
                if filename.find("D.TIF")!=-1:
                    dird = dirname
                    countd +=1
                if filename.find("F.TIF")!=-1:
                    dirf = dirname
                    countf +=1
                if filename.find("R.TIF")!=-1:
                    dirr = dirname
                    countr +=1
                zfile.extract(name, datasetinputfolder)
                
        if countd==1 and countf==1 and countr==1 and dird == dirf and dird == dirr:

            subprocess.check_output(['CellProfiler.exe', '-c', '-r', '-i',  dird, '-o', datasetoutputfolder, '-p', pipelinepath], stderr=subprocess.STDOUT)

            generated_files = []
            for f in os.listdir(datasetoutputfolder):
                if f.lower().endswith(".csv") or f.lower().endswith(".tif") or f.lower().endswith(".tiff"):
                    # upload the file to the dataset
                    new_fid=extractors.upload_file_to_dataset(os.path.join(datasetoutputfolder,f), parameters)
                    new_url=extractors.get_file_URL(fileid=new_fid, parameters=parameters)
                    generated_files.append(new_url)


            mdata = {}
            mdata["extractor_id"]=extractorName
            mdata["generated_files"]=generated_files

            for f in os.listdir(datasetoutputfolder):
                filemeta={}
                filepath = os.path.join(datasetoutputfolder,f)
                if f.endswith(".csv"):
                    metarows=[]
                    with open(filepath, 'rb') as csvfile:
                        reader = csv.reader(csvfile, delimiter=',')
                        header = reader.next()
                        for row in reader:
                            metarow={}
                            for cell in range(0, len(row)-1):
                                metarow[header[cell]]=row[cell]
                            metarows.append(metarow)
                    metafield=f[f.rindex('_')+1:f.rindex('.')]
                    mdata[metafield]=metarows
            
            extractors.upload_file_metadata(mdata=mdata, parameters=parameters)


    finally:
        if os.path.isdir(datasetinputfolder):
            try:
                shutil.rmtree(datasetinputfolder)
            except:
                pass
        if os.path.isdir(datasetoutputfolder):
            try:
                shutil.rmtree(datasetoutputfolder)
            except:
                pass



if __name__ == "__main__":
    main()