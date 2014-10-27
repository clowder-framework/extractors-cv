#!/usr/bin/env python
import pika
import sys
import logging
import json
import traceback
import requests
import tempfile
import subprocess
import os
import itertools
import time
from subprocess import Popen, PIPE
from config import *


def extract_handwritten_numbers(inputfile, host, fileid, key):
	global logger
	global extractorName
	global matlab_process
	global sslVerify

	logger.debug("starting handwritten numbers extraction process")
	
	tmpfile=inputfile+".txt"

	try:
		# call matlab code to classify image
		extract_command = "handwritten_numbers_extract('"+inputfile+"', '"+tmpfile+"')\n"
		matlab_process.stdin.write(extract_command)
		matlab_process.stdin.flush()

		#wait for result file (tmpfile) to be created
		while (not os.path.isfile(tmpfile)):
			time.sleep(0.5)

		numbers=[]
		#tmpfile resulting from running the matlab code should contain one line per number
		with open(tmpfile, 'r') as fd:
			for line in fd:
				number = line.strip('\n')
				numbers.append(number)

		headers={'Content-Type': 'application/json'}

		url=host+'api/files/'+ fileid +'/metadata?key=' + key
		mdata={}
		mdata["extractor_id"]=extractorName
		mdata["sphog_numbers"]=numbers
		
		logger.debug("metadata: %s",json.dumps(mdata))
		rt = requests.post(url, headers=headers, data=json.dumps(mdata), verify=sslVerify)
		rt.raise_for_status()
		logger.debug("[%s] finished running numbers extractor", fileid)

	finally:
		os.remove(tmpfile)
		logger.debug("[%s] done with basic sphog numbers extractor", fileid)  



def main():
	global extractorName, rabbitmqUsername, rabbitmqURL, rabbitmqPort, rabbitmqPassword, messageType, exchange, rabbitmqHost
	global logger
	global matlab_process

	install_folder=os.path.dirname(os.path.realpath(__file__))
	# open matlab, go to required directory, and keep it running
	matlab_process = subprocess.Popen(['matlab', '-nodesktop', '-noFigureWindows', '-nosplash', '-r'], stdin=PIPE, stdout=PIPE, shell=True);
	cd_command="cd '"+install_folder+"'\n"
	matlab_process.stdin.write(cd_command)
	matlab_process.stdin.flush()
	time.sleep(1) 
	# setup
	matlab_process.stdin.write("handwritten_digit_extractor_main;\n")
	matlab_process.stdin.flush()
	time.sleep(5) 

	# configure the logging system
	logging.basicConfig(format="%(asctime)-15s %(name)-10s %(levelname)-7s : %(message)s", level=logging.WARN)
	logger = logging.getLogger(extractorName)
	logger.setLevel(logging.DEBUG)

	# connect to rabbitmq using input username and password
	if (rabbitmqURL is None):
		if (rabbitmqUsername is not None and rabbitmqPassword is not None):
			credentials = pika.PlainCredentials(rabbitmqUsername, rabbitmqPassword)
		else:
			credentials = None
		parameters = pika.ConnectionParameters(host=rabbitmqHost, port=rabbitmqPort, credentials=credentials)
	else:
		parameters = pika.URLParameters(rabbitmqURL)
	connection = pika.BlockingConnection(parameters)

		
	# connect to channel
	channel = connection.channel()

	# declare the exchange
	channel.exchange_declare(exchange=exchange, exchange_type='topic', durable=True)

	# declare the queue
	channel.queue_declare(queue=extractorName, durable=True)

	# connect queue and exchange
	channel.queue_bind(queue=extractorName, exchange=exchange, routing_key=messageType)

	# setting prefetch count to 1 as workarround pika 0.9.14
	channel.basic_qos(prefetch_count=1)

	# start listening
	logger.info("Waiting for messages. To exit press CTRL+C")

	# create listener
	channel.basic_consume(on_message, queue=extractorName, no_ack=False)

	try:
		channel.start_consuming()
	except KeyboardInterrupt:
		channel.stop_consuming()

	# close connection
	connection.close()

	# kill matlab
	matlab_process.stdin.write("quit()\n")
	matlab_process.stdin.flush()
	matlab_process.kill()
		 

def on_message(channel, method, header, body):
	global logger
	global extractorName
	global sslVerify
	
	statusreport = {}

	inputfile=None
	try:
		# parse body back from json
		jbody=json.loads(body)
		key=jbody['secretKey']
		host=jbody['host']
		#logger.debug("host[%s]=",host)
		fileid=jbody['id']
		if not (host.endswith('/')):
			host += '/'

		# print what we are doing
		logger.debug("[%s] started processing", fileid)
		# for status reports
		statusreport['file_id'] = fileid
		statusreport['extractor_id'] = extractorName
		statusreport['status'] = 'Downloading image file.'
		statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
		statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')

		channel.basic_publish(exchange='',
							routing_key=header.reply_to,
							properties=pika.BasicProperties(correlation_id = \
														header.correlation_id),
							body=json.dumps(statusreport)) 

		# fetch data
		url=host + 'api/files/' + fileid + '?key=' + key
		r=requests.get(url, stream=True, verify=sslVerify)
		r.raise_for_status()
		(fd, inputfile)=tempfile.mkstemp()
		with os.fdopen(fd, "w") as f:
			for chunk in r.iter_content(chunk_size=10*1024):
				f.write(chunk)

		statusreport['status'] = 'Extracting handwritten digit and associating with file.'
		statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
		statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')

		channel.basic_publish(exchange='',
							routing_key=header.reply_to,
							properties=pika.BasicProperties(correlation_id = \
														header.correlation_id),
							body=json.dumps(statusreport))



		extract_handwritten_numbers(inputfile, host, fileid, key)

	except subprocess.CalledProcessError as e:
		logger.exception("[%s] error processing [exit code=%d]\n%s", fileid, e.returncode, e.output)
		statusreport['status'] = 'Error processing.'
		statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S') 
		statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')

		channel.basic_publish(exchange='',
				routing_key=header.reply_to,
				properties=pika.BasicProperties(correlation_id = \
												header.correlation_id),
				body=json.dumps(statusreport)) 
	except:
		logger.exception("[%s] error processing", fileid)
		statusreport['status'] = 'Error processing.'
		statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S') 
		statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')

		channel.basic_publish(exchange='',
				routing_key=header.reply_to,
				properties=pika.BasicProperties(correlation_id = \
												header.correlation_id),
				body=json.dumps(statusreport)) 
	finally:
		statusreport['status'] = 'DONE.'
		statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
		statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')

		channel.basic_publish(exchange='',
							routing_key=header.reply_to,
							properties=pika.BasicProperties(correlation_id = \
														header.correlation_id),
							body=json.dumps(statusreport))
		if inputfile is not None:
			os.remove(inputfile)

		# Ack
		channel.basic_ack(method.delivery_tag)
		logger.debug("[%s] finished processing", fileid)


if __name__ == "__main__":
	main()
