FROM python:3-alpine

RUN apk update
RUN apk add make automake gcc g++ subversion python3-dev

RUN pip3 install pandas

ADD . .
