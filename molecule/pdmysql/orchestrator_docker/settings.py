import os

orch_version = os.getenv('OCHESTARTOR_VERSION')
docker_acc = os.getenv('DOCKER_ACC')
orch_tag = os.getenv('ORCHESTRATOR_TAG')

docker_product = 'percona-orchestrator'
docker_tag = orch_tag
docker_image = docker_acc + "/" + docker_product + ":" + docker_tag


RHEL_DISTS = ["redhat", "centos", "rhel", "oracleserver", "ol", "amzn"]

DEB_DISTS = ["debian", "ubuntu"]
