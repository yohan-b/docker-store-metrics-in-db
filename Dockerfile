FROM debian:buster
MAINTAINER yohan <783b8c87@scimetis.net>
ENV DEBIAN_FRONTEND noninteractive
ENV TZ Europe/Paris
RUN apt-get update && apt-get -y install python-pip python-mysqldb python-yaml
RUN pip install flask-restx flask-sqlalchemy flask-migrate
WORKDIR /root
COPY api.py /root/
COPY migrate_db.sh /root/
COPY entrypoint.sh /root/
ENTRYPOINT ["/root/entrypoint.sh"]
