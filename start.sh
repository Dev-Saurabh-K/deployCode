#!/bin/bash

cd /home/saurabh/deployCode

source .venv/bin/activate

nohup gunicorn main:app -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8080 --access-logfile - --error-logfile -  > server.log 2>&1 &
