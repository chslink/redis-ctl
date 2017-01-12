FROM python:2-alpine
MAINTAINER blless<blless@qq.com>
ENV TZ Asia/Shanghai
ENV APP_ROOT /code
RUN echo 'http://mirrors.aliyun.com/alpine/v3.4/main/' > /etc/apk/repositories
RUN apk --update --no-cache add gcc linux-headers musl-dev libffi-dev openssl-dev
RUN mkdir ~/.pip &&\
    echo -e "[global] \nindex-url = http://mirrors.aliyun.com/pypi/simple/ \n[install] \ntrusted-host=mirrors.aliyun.com" > ~/.pip/pip.conf

WORKDIR ${APP_ROOT}
COPY requirements.txt ${APP_ROOT}/
RUN pip install --no-cache-dir --upgrade --force-reinstal -r requirements.txt
