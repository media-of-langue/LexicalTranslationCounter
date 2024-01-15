ARG LANG_A
ARG LANG_B
ARG TAG_WORDLIST
ARG TAG_CORPUS
FROM mediaoflangue/wordlist_${LANG_A}:${TAG_WORDLIST} AS wordlist1
FROM mediaoflangue/wordlist_${LANG_B}:${TAG_WORDLIST} AS wordlist2
FROM mediaoflangue/corpus_${LANG_A}_${LANG_B}:${TAG_CORPUS} AS corpus
FROM nvidia/cuda:11.6.2-base-ubuntu20.04
COPY --from=wordlist1 /src/data/input/wordlist* /root/src/data/input/
COPY --from=wordlist2 /src/data/input/wordlist* /root/src/data/input/
COPY --from=corpus /src/data/input/corpus* /root/src/data/input/
ENV JAVA_HOME /usr/lib/jvm/java-1.7-openjdk/jre
ARG SRCDIR=/src
RUN export LC_ALL=C.UTF-8
RUN export LANG=C.UTF-8
ARG LANG_A
ARG LANG_B
COPY ./shell_scripts/basis ./basis/
COPY ./shell_scripts/${LANG_A} ./${LANG_A}/
COPY ./shell_scripts/${LANG_B} ./${LANG_B}/
COPY ./shell_scripts/${LANG_A}-${LANG_B} ./${LANG_A}-${LANG_B}
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
RUN cd /${LANG_A} && sh ./install.sh
RUN cd /${LANG_B} && sh ./install.sh
RUN cd /${LANG_A}-${LANG_B} && sh ./install.sh
WORKDIR ${SRCDIR}
COPY .${SRCDIR} /root/src/

CMD [ "/bin/bash" ]