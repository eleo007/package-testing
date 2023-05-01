#!/usr/bin/env python3
import pytest
import subprocess
import testinfra
import json
import time
from settings import *

orch_container_name = 'orchestartor-docker-test-dynamic'
ps_container_name = 'ps-docker'
source_ps_container_name = 'ps-docker-source'
replica_ps_container_name = 'ps-docker-replica'
network_name = 'orchestrator'

@pytest.fixture(scope='module')
def host():
    subprocess.check_call(['docker', 'network', 'create', network_name])
    orch_docker_id = subprocess.check_output(
        ['docker', 'run', '--name', orch_container_name, '-d', '--network', network_name, docker_image ]).decode().strip()
    time.sleep(20)
    source_ps_docker_id = subprocess.check_output(
        ['docker', 'run', '--name', source_ps_container_name, '-e', 'MYSQL_ROOT_PASSWORD=secret', '-d', '--network', network_name, ps_docker_image,
        '--log-error-verbosity=3', '--report_host="'+source_ps_container_name+'"', '--max-allowed-packet=134217728']).decode().strip()
    time.sleep(20)
    replica_ps_docker_id = subprocess.check_output(
        ['docker', 'run', '--name', replica_ps_container_name, '-e', 'MYSQL_ROOT_PASSWORD=secret', '-d', '--network', network_name, ps_docker_image, 
        '--log-error-verbosity=3', '--report_host="'+replica_ps_container_name+'"', '--max-allowed-packet=134217728', '--server-id=2']).decode().strip()
    time.sleep(20)
    subprocess.check_call(['docker', 'exec', source_ps_docker_id, 'mysql', '-uroot', '-psecret', '-e', 'CREATE USER \'repl\'@\'%\' IDENTIFIED WITH mysql_native_password BY \'replicapass\'; GRANT REPLICATION SLAVE ON *.* TO \'repl\'@\'%\';'])
    subprocess.check_call(['docker', 'exec', replica_ps_docker_id, 'mysql', '-uroot', '-psecret', '-e', 'CHANGE REPLICATION SOURCE to SOURCE_HOST="'+source_ps_container_name+'",SOURCE_USER="repl",SOURCE_PASSWORD="replicapass",SOURCE_LOG_FILE="binlog.000002";show warnings;'])
    subprocess.check_call(['docker', 'exec', replica_ps_docker_id, 'mysql', '-uroot', '-psecret', '-e', 'START REPLICA;'])
    # yield testinfra.get_host("docker://root@" + orch_docker_id)
    # subprocess.check_call(['docker', 'rm', '-f', orch_docker_id])

def test_packages(self, host):
    cmd=host.run('echo \'some command\'')
    assert cmd.succeeded