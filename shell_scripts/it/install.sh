#AVA_HOME = '/usr/lib/jvm/java-1.7-openjdk/jre'
#apt-get install -y openjdk-11-jre
#pip3 install --upgrade --force-reinstall setuptools cython numpy
#pip3 install numpy==1.18.5
#pip3 install spacy
pip3 install -r ./requirements.txt
python3 -m spacy download "it_core_news_sm"