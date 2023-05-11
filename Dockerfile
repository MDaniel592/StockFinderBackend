# Pull official base image
FROM python:3.10.9-slim-buster

# Install the requirements packages
RUN apt-get update && apt-get install apt-utils libpq-dev gcc -y

# Install dependencies
WORKDIR /usr/src/app
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN python3 -m pip install -r requirements.txt --no-cache-dir

# Copy project
COPY . /usr/src/app/

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV LANG en_US.UTF-8  
ENV LANGUAGE en_US:en  
ENV LC_ALL en_US.UTF-8
ENV FLASK_APP server.py
ENV FLASK_DEBUG 1

# Variables ocultas del fichero .env
ENV JWT_AUTH_SECRET=${JWT_AUTH_SECRET}
ENV FLASK_AUTH_SECRET=${FLASK_AUTH_SECRET}
ENV HOSTNAME=${HOSTNAME}

ENV POSGRESQL_DATABASE=${POSGRESQL_DATABASE}
ENV POSGRESQL_LOCAL_URL=${POSGRESQL_LOCAL_URL}
ENV POSGRESQL_LOCAL_PORT=${POSGRESQL_LOCAL_PORT}
ENV POSGRESQL_LOCAL_USER=${POSGRESQL_LOCAL_USER}
ENV POSGRESQL_LOCAL_USER_PASSWORD=${POSGRESQL_LOCAL_USER_PASSWORD}
ENV POSGRESQL_REMOTE_URL=${POSGRESQL_REMOTE_URL}
ENV POSGRESQL_REMOTE_PORT=${POSGRESQL_REMOTE_PORT}
ENV POSGRESQL_REMOTE_USER=${POSGRESQL_REMOTE_USER}
ENV POSGRESQL_REMOTE_USER_PASSWORD=${POSGRESQL_REMOTE_USER_PASSWORD}

ENV MAIL_SMTP_SERVER=${MAIL_SMTP_SERVER}
ENV MAIL_SMTP_PORT=${MAIL_SMTP_PORT}
ENV MAIL_SENDER_EMAIL=${MAIL_SENDER_EMAIL}
ENV MAIL_USERNAME=${MAIL_USERNAME}
ENV MAIL_PASSWORD=${MAIL_PASSWORD}

ENV TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}

ENV HCAPTCHA_SITE_KEY=${HCAPTCHA_SITE_KEY}
ENV HCAPTCHA_SECRET_KEY=${HCAPTCHA_SECRET_KEY}

# Export port
EXPOSE ${DOCKER_BACKEND_PORT}

# Start
ENTRYPOINT ["sh","/usr/src/app/gunicorn.sh"]
