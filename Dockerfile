FROM ubuntu:20.04

# install pip and binaries used by python-ldap
RUN apt-get update -y && \
    apt-get install -y python3 python3-pip libpq-dev libpcre3 libpcre3-dev git

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install -r requirements.txt

COPY . /app

ENV FLASK_APP=app.py
ENV AUTHLIB_INSECURE_TRANSPORT=1

ENTRYPOINT [ "uwsgi", "--http-socket", "0.0.0.0:5002", "--processes", "16", "--wsgi-file", "app.py",  "--callable", "app","--log-master", "--enable-threads"]