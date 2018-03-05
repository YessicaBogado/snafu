FROM alpine:3.7

RUN apk add --no-cache python3 && \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
    if [[ ! -e /usr/bin/python ]]; then ln -sf /usr/bin/python3 /usr/bin/python; fi && \
    rm -r /root/.cache
# RUN apk add --no-cache git && git clone https://github.com/YessicaBogado/snafu /home/snafu
RUN apk update && apk add cython-dev && apk add python3-dev && apk add build-base && \
    apk add openjdk8 && apk add openjdk8-jre
RUN pip3 install pyinotify boto3 flask && apk add inotify-tools
COPY . /home/snafu/
RUN cd /home/snafu && python3 setup.py build && python3 setup.py install
RUN chmod 0775 -R /home/snafu/

ENV HOME /home/snafu
ENV JAVA_HOME /usr/lib/jvm/java-1.8-openjdk
ENV PATH $PATH:$JAVA_HOME/bin

RUN mkdir $HOME/functions-local

WORKDIR /home/snafu

EXPOSE 10000

USER 1001

CMD ["/bin/sh", "-c", "(/home/snafu/mon.sh &) && /home/snafu/snafu -C web -s /home/snafu/snafu.ini.dist"]
