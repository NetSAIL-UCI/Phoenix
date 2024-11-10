
sudo add-apt-repository ppa:deadsnakes/ppa; sudo apt update; sudo apt -y install python3.9; sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 2; sudo apt-get -y install python3-pip
# install kubernetes package
sudo apt-get -y install python3.9-distutils; python3 -m pip install kubernetes; python3 -m pip install networkx; python3 -m pip install numpy; python3 -m pip install requests; python3 -m pip install sortedcontainers; python3 -m pip install matplotlib
kubectl label node node-24 nodes=24
kubectl label node node-20 nodes=20
kubectl label node node-21 nodes=21
kubectl label node node-22 nodes=22
kubectl label node node-23 nodes=23
kubectl label node node-11 nodes=11
kubectl label node node-10 nodes=10
kubectl label node node-13 nodes=13
kubectl label node node-12 nodes=12
kubectl label node node-15 nodes=15
kubectl label node node-14 nodes=14
kubectl label node node-17 nodes=17
kubectl label node node-16 nodes=16
kubectl label node node-19 nodes=19
kubectl label node node-18 nodes=18
kubectl label node node-5 nodes=5
kubectl label node node-4 nodes=4
kubectl label node node-7 nodes=7
kubectl label node node-6 nodes=6
kubectl label node node-1 nodes=1
kubectl label node node-0 nodes=0
kubectl label node node-3 nodes=3
kubectl label node node-2 nodes=2
kubectl label node node-9 nodes=9
kubectl label node node-8 nodes=8

kubectl delete all --all
kubectl delete pvc --all
kubectl delete pv --all
curl -L https://istio.io/downloadIstio | sh -

cd istio-1.19.3/
# setenv PATH $PWD/bin:$PATH
export PATH = $PWD/bin:$PATH
istioctl install

wget https://packages.gurobi.com/10.0/gurobi10.0.3_linux64.tar.gz
tar -xvf gurobi10.0.3_linux64.tar.gz

setenv GUROBI_HOME gurobi1003/linux64
setenv PATH ${PATH}:${GUROBI_HOME}/bin
setenv LD_LIBRARY_PATH ${GUROBI_HOME}/lib

echo "Done! Press Enter twice"

