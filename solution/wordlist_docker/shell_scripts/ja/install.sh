apt-get install -y wget clang cmake xz-utils 
pip3 install -r ./requirements.txt
wget https://github.com/ku-nlp/jumanpp/releases/download/v2.0.0-rc3/jumanpp-2.0.0-rc3.tar.xz 
tar xvf jumanpp-2.0.0-rc3.tar.xz 
cd jumanpp-2.0.0-rc3 
mkdir bld 
cd bld 
cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local 
make install -j 4