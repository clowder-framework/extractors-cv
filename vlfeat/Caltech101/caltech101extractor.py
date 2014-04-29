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

def extract_caltech101_category(inputfile, host, fileid, key):
	global logger
	global receiver
	global matlab_process

	logger.debug("starting classification process")
	
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

		headers={'Content-Type': 'application/json'}

		url=host+'api/files/'+ fileid +'/metadata?key=' + key
		mdata={}
		mdata["extractor_id"]=receiver
		mdata["basic_caltech101_category"]=[category]
		mdata["basic_caltech101_score"]=[score]

		logger.debug("metadata: %s",json.dumps(mdata))
		rt = requests.post(url, headers=headers, data=json.dumps(mdata))
		rt.raise_for_status()
		logger.debug("[%s] finished running classifier", fileid)

	finally:
		os.remove(tmpfile)
		logger.debug("[%s] done with basic caltech 101 category extractor", fileid)  



def main():
	global logger
	global receiver
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

	# name of receiver
	receiver='ncsa.image.caltech101'

	# configure the logging system
	logging.basicConfig(format="%(asctime)-15s %(name)-10s %(levelname)-7s : %(message)s", level=logging.WARN)
	logger = logging.getLogger(receiver)
	logger.setLevel(logging.DEBUG)

	# connect to rabitmq
	connection = pika.BlockingConnection()

	# connect to channel
	channel = connection.channel()

	# declare the exchange
	channel.exchange_declare(exchange='medici', exchange_type='topic', durable=True)

	# declare the queue
	channel.queue_declare(queue=receiver, durable=True)

	# connect queue and exchange
	channel.queue_bind(queue=receiver, exchange='medici', routing_key='*.file.image.#')

	# create listener
	channel.basic_consume(on_message, queue=receiver, no_ack=False)

	# start listening
	logger.info("Waiting for messages. To exit press CTRL+C")
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
	global receiver
	statusreport = {}

	inputfile=None
	try:
		# parse body back from json
		jbody=json.loads(body)

		# key=jbody['key']
		key='r1ek3rs'
		host=jbody['host']
		#logger.debug("host[%s]=",host)
		fileid=jbody['id']
		if not (host.endswith('/')):
			host += '/'

		# print what we are doing
		logger.debug("[%s] started processing", fileid)
		# for status reports
		statusreport['file_id'] = fileid
		statusreport['extractor_id'] = receiver
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
		r=requests.get(url, stream=True)
		r.raise_for_status()
		(fd, inputfile)=tempfile.mkstemp()
		with os.fdopen(fd, "w") as f:
			for chunk in r.iter_content(chunk_size=10*1024):
				f.write(chunk)

		statusreport['status'] = 'Extracting Caltech 101 category and associating with file.'
		statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
		statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')
		channel.basic_publish(exchange='',
							routing_key=header.reply_to,
							properties=pika.BasicProperties(correlation_id = \
														header.correlation_id),
							body=json.dumps(statusreport))



		extract_caltech101_category(inputfile, host, fileid, key)
		

		# Ack
		channel.basic_ack(method.delivery_tag)
		logger.debug("[%s] finished processing", fileid)
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


if __name__ == "__main__":
	main()