FROM python:3.8-slim

RUN pip3 install pandas

RUN apt-get update
RUN apt-get -y install git && git clone https://github.com/armanschwarz/gnc_tools.git

ADD src/*.py /usr/local/bin/
