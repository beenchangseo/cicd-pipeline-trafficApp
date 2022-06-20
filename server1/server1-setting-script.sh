#!/bin/bash

#환경 변수 설정
PATH_NAME=/root/pipline-server
if [ -f $PATH_NAME/.env ]; then
  export $(grep -v '^#' $PATH_NAME/.env | xargs)
fi

# yum update
yum -y update

# 유저 추가 및 권한 설정
useradd -m $SERVER1_USER
echo $PASSWORD | passwd --stdin $SERVER1_USER
usermod -aG wheel $SERVER1_USER
echo $SERVER1_USER " ALL=(ALL)  ALL" | sudo tee /etc/sudoers.d/$SERVER1_USER

# hostname 변경
hostnamectl set-hostname $SERVER1_USER

# python3.8 version install
cd ~
yum -y groupinstall 'Development Tools'
yum -y install zlib zlib-devel libffi-devel
yum -y install openssl openssl-devel
curl -O https://www.python.org/ftp/python/3.8.1/Python-3.8.1.tgz
tar zxvf Python-3.8.1.tgz
cd Python-3.8.1
./configure
make
make install

# pip3 update & install modules
pip3 install --upgrade pip
pip3 install kafka-python==2.0.2
pip3 install python-socketio==5.5.0
pip3 install pymysql==1.0.2
pip3 install openpyxl==3.0.9
pip3 install sysv-ipc==1.1.0
pip3 install aiohttp==3.7.4.post0
pip3 install requests==2.26.0
pip3 install python-dotenv
pip3 install psycopg2-binary

# nodejs LTS version install #
cd ~
curl -sL https://rpm.nodesource.com/setup_lts.x | sudo -E bash -
yum -y install nodejs

# docker install
yum install -y yum-utils
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce docker-ce-cli containerd.io
systemctl start docker
systemctl enable docker

# docker compose install
sudo curl -L "https://github.com/docker/compose/releases/download/1.28.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
docker-compose --version

# f/w ports open
firewall-cmd --zone=public --permanent --add-port=2377/tcp
firewall-cmd --zone=public --permanent --add-port=2377/udp
firewall-cmd --zone=public --permanent --add-port=7946/tcp
firewall-cmd --zone=public --permanent --add-port=7946/udp
firewall-cmd --zone=public --permanent --add-port=4789/tcp
firewall-cmd --zone=public --permanent --add-port=4789/udp
firewall-cmd --permanent --zone=public --add-port=2181/tcp
firewall-cmd --permanent --zone=public --add-port=2888/tcp
firewall-cmd --permanent --zone=public --add-port=3888/tcp
firewall-cmd --permanent --zone=public --add-port=9092/tcp
firewall-cmd --permanent --zone=public --add-port=9093/tcp
firewall-cmd --add-service=ntp --permanent
firewall-cmd --reload

#ntp server
yum install -y ntp
\cp /root/cicd-pipeline-trafficApp/ntp.conf /etc/ntp.conf
systemctl start ntpd
systemctl enable ntpd
systemctl status ntpd

#docker swarm init
echo ""
echo ""
echo "[SWARM INIT] 1. Docker Swarm init >> /root/swarmpool.txt"
docker swarm init --advertise-addr $SERVER1_IP | grep -- --token > /root/swarmpool.txt
echo ""
echo ""
echo ""
echo "[SWARM INIT] 2. Overlay Network init"
docker network create --attachable --driver overlay cluster_net
echo "[SWARM INIT COMPLETE]"
echo ""
echo ""
echo ""
echo "[KAFKA CLUSTER] To add docker container, run this command...."
echo "docker-compose --env-file ../.env up -d"
echo "[KAFKA CLUSTER COMPLETE]"