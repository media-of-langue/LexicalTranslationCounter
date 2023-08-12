ARG LA1
ARG LA2
FROM mediaoflangue/wordlist_${LA1}:latest AS wordlist1
FROM mediaoflangue/wordlist_${LA2}:latest AS wordlist2
FROM mediaoflangue/corpus_${LA1}_${LA2}:latest AS corpus
FROM nvidia/cuda:11.6.2-base-ubuntu20.04
COPY --from=wordlist1 /src/data/input/wordlist* /root/src/data/input/
COPY --from=wordlist2 /src/data/input/wordlist* /root/src/data/input/
COPY --from=corpus /src/data/input/corpus* /root/src/data/input/
ENV JAVA_HOME /usr/lib/jvm/java-1.7-openjdk/jre
ARG SRCDIR=/src
RUN export LC_ALL=C.UTF-8
RUN export LANG=C.UTF-8
ARG LA1
ARG LA2
COPY ./shell_scripts/basis ./basis/
COPY ./shell_scripts/${LA1} ./${LA1}/
COPY ./shell_scripts/${LA2} ./${LA2}/
COPY ./shell_scripts/${LA1}-${LA2} ./${LA1}-${LA2}
RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y \
    locales \
    locales-all \
    g++ \
    default-jdk && \
    locale-gen ja_JP.UTF-8 && \
    echo "export LANG=ja_JP.UTF-8" >> ~/.bashrc 
RUN apt-get install -y python3 python3-pip
RUN pip3 install --upgrade pip
RUN cd ./basis/ && sh ./install.sh
RUN cd /${LA1} && sh ./install.sh
RUN cd /${LA2} && sh ./install.sh
RUN cd /${LA1}-${LA2} && sh ./install.sh
WORKDIR ${SRCDIR}
COPY .${SRCDIR} /root/src/

CMD [ "/bin/bash" ]