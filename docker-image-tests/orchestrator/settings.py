import os

orch_version = os.getenv('OCHESTARTOR_VERSION')
docker_tag = os.getenv('OCHESTARTOR_VERSION')
ps_docker_tag = os.getenv('PS_VERSION')
docker_acc = os.getenv('DOCKER_ACC')

docker_product = 'percona-orchestrator'
ps_docker_product = 'percona-server'
docker_image = docker_acc + "/" + docker_product + ":" + docker_tag
ps_docker_image = docker_acc + "/" + ps_docker_product + ":" + ps_docker_tag

RHEL_DISTS = ["redhat", "centos", "rhel", "oracleserver", "ol", "amzn"]

DEB_DISTS = ["debian", "ubuntu"]
