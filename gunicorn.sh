#!/bin/bash
gunicorn --workers 4 --bind 0.0.0.0:6000 server:app