FROM debian:buster
MAINTAINER yohan <783b8c87@scimetis.net>
ENV DEBIAN_FRONTEND noninteractive
ENV TZ Europe/Paris
RUN apt-get update && apt-get -y install python-pip python-mysqldb python-yaml
RUN pip install pyrsistent==0.16.0
RUN pip install "jsonschema<4.0"
RUN pip install flask-restx==1.3.0
RUN pip install flask-sqlalchemy
WORKDIR /root
COPY api.py /root/
COPY entrypoint.sh /root/
ENTRYPOINT ["/root/entrypoint.sh"]
