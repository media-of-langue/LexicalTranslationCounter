ARG LA1=en
ARG LA2=it
FROM mediaoflangue/wordlist_${LA1}:latest AS wordlist1
FROM aaakmn/wordlist_${LA2}:latest AS wordlist2
FROM aaakmn/corpus_${LA1}_${LA2}:latest AS corpus
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

WORKDIR ${SRCDIR}
COPY .${SRCDIR} /root/src/

CMD [ "/bin/bash" ]