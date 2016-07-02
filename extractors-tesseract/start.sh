#!/bin/bash

if [ "$RABBITMQ_URI" == "" ]; then
    if [ -n $RABBITMQ_PORT_5672 ]; then
        RABBITMQ_URI="amqp://guest:guest@${RABBITMQ_PORT_5672_TCP_ADDR}:${RABBITMQ_PORT_5672_TCP_PORT}/%2F"
    else
        RABBITMQ_URI="amqp://guest:guest@localhost:5672/%2F"
    fi
fi

cd $CLOWDER_HOME
exec ./ocr.py
