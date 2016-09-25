FROM ubuntu:14.04

WORKDIR /opt

RUN apt-get update && apt-get install -y \
    build-essential \
    ca-certificates \
    wget \
    curl \
    unzip \
    git \
    libcurl4-gnutls-dev \
    libgnutls-dev \
    python \
    python-dev \
    python-pip \
    pypy

RUN pip install --upgrade pip
RUN pip install --upgrade virtualenv
RUN pip install numpy
RUN pip install PyVCF

ENV APP_NAME=bowtie2
ENV VERSION=v2.2.9
ENV GIT=https://github.com/BenLangmead/bowtie2.git
ENV DEST=/software/applications/$APP_NAME/
ENV PATH=$DEST/$VERSION/:$DEST/$VERSION/scripts/:$PATH

RUN git clone $GIT ; \
    cd $APP_NAME ; \
    git checkout tags/$VERSION ; \
    sed -i "s#^prefix.*#prefix = $DEST#" Makefile ; \
    make -j ; \
    mkdir -p /usr/share/licenses/$APP_NAME-$VERSION ; \
    cp LICENSE /usr/share/licenses/$APP_NAME-$VERSION/ ; \
    cd ../ ;  \
    mkdir -p $DEST ; \
    mv $APP_NAME $DEST/$VERSION
