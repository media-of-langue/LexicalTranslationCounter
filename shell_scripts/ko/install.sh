AVA_HOME = '/usr/lib/jvm/java-1.7-openjdk/jre'
apt-get install -y openjdk-11-jre
pip3 install -r ./requirements.txt
pip3 install spacy
python3 -m spacy download "ko_core_news_sm"