# cicd-pipeline-trafficApp
> Real-time traffic monitoring & control application server setting script
---
### Stack
<p>
    <img alt="Python" src ="https://img.shields.io/badge/Docker-2496ED.svg?&style=for-the-badge&logo=Docker&logoColor=white"/>
    <img alt="Python" src ="https://img.shields.io/badge/Shell-FFD500.svg?&style=for-the-badge&logo=Shell&logoColor=white"/>
    <img alt="Python" src ="https://img.shields.io/badge/PostgreSQL-4169E1.svg?&style=for-the-badge&logo=PostgreSQL&logoColor=white"/>
</p>

---
### Architecture (CentOS 7)
> We will create a kafka cluster with 3 nodes\
> You can edit 3 nodes ip and hostname with '.env' file

| IP           | Hostname | Componets                            |
|--------------| -------- |--------------------------------------|
| 172.16.0.201 | node1    | docker, zookeeper, kafka,            |
| 172.16.0.202 | node2    | docker, zookeeper, kafka, postgresql |
| 172.16.0.203 | node3    | docker, zookeeper, kafka,            |

---
### Usage
 **node 1**
 
 ```bash
  sh server1/server1-setting-script.sh
 ```