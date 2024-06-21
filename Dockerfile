FROM debian:bookworm
MAINTAINER yohan <783b8c87@scimetis.net>
ENV DEBIAN_FRONTEND noninteractive
ENV TZ Europe/Paris
RUN apt-get update && apt-get -y install gunicorn python3-pip python3-yaml python3-flask python3-mysqldb
ENV PIP_BREAK_SYSTEM_PACKAGES 1
RUN pip install flask-restx==1.3.0
RUN pip install flask-sqlalchemy
WORKDIR /root
COPY api.py /root/
COPY entrypoint.sh /root/
ENTRYPOINT ["/root/entrypoint.sh"]
