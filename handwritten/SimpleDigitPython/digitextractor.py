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
import cv2
import digits

sslVerify=False

def extract_digit(inputfile, host, fileid, key):
	global logger
	global model
	global receiver
	global sslVerify

	logger.debug("starting classification process")
	
	try:
		# load image as grayscale
		digit = cv2.imread(inputfile, 0)
		# resize it so it fits the image dimensions of the ones in the training set
		digit_norm = cv2.resize(digit, (28 ,28))
		digit2 = digits.deskew(digit_norm)
		#get hog samples
		samples = digits.preprocess_hog([digit2])
		#uses loaded model to classify samples
		resp = model.predict(samples)

		headers={'Content-Type': 'application/json'}

		url=host+'api/files/'+ fileid +'/metadata?key=' + key
		mdata={}
		mdata["extractor_id"]=receiver
		mdata["basic_digitpy"]=resp

		logger.debug("metadata: %s",json.dumps(mdata))
		rt = requests.post(url, headers=headers, data=json.dumps(mdata), verify=sslVerify)
		rt.raise_for_status()
		logger.debug("[%s] finished running classifier", fileid)

	finally:
		logger.debug("[%s] done with basic python digit extractor", fileid)  



def main():
	global logger
	global model
	global receiver

	# install_folder=os.path.dirname(os.path.realpath(__file__))
	model = digits.SVM(C=2.67, gamma=5.383)
	model.load('digits_svm.dat')

	# name of receiver
	receiver='ncsa.image.digitpy'

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
		 

def on_message(channel, method, header, body):
	global logger
	global receiver
	global sslVerify
	
	statusreport = {}

	inputfile=None
	try:
		# parse body back from json
		jbody=json.loads(body)
		key=jbody['key']
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
		r=requests.get(url, stream=True, verify=sslVerify)
		r.raise_for_status()
		(fd, inputfile)=tempfile.mkstemp()
		with os.fdopen(fd, "w") as f:
			for chunk in r.iter_content(chunk_size=10*1024):
				f.write(chunk)

		statusreport['status'] = 'Extracting digit and associating with file.'
		statusreport['start'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        statusreport['end']=time.strftime('%Y-%m-%dT%H:%M:%S')

		channel.basic_publish(exchange='',
							routing_key=header.reply_to,
							properties=pika.BasicProperties(correlation_id = \
														header.correlation_id),
							body=json.dumps(statusreport))



		extract_digit(inputfile, host, fileid, key)
		
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