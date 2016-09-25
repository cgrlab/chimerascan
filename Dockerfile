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

RUN wget -qO /home/user/bin/bowtie2-2.2.9-linux-x86_64.zip \ 
    https://sourceforge.net/projects/bowtie-bio/files/bowtie2/2.2.9/bowtie2-2.2.9-linux-x86_64.zip/download \
    && unzip -d /home/user/bin/bowtie2-2.2.9 /home/user/bin/bowtie2-2.2.9-linux-x86_64.zip \
    && rm /home/user/bin/bowtie2-2.2.9-linux-x86_64.zip \
    && find /home/user/bin/bowtie2-2.2.9 -perm /a+x -type f -exec mv {} /usr/local/bin \; \
    && rm -rf -- /home/user/bin/bowtie2-2.2.9
    
