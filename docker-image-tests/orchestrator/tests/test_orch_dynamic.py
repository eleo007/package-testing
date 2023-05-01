#!/usr/bin/env python3
import pytest
import subprocess
import testinfra
import json
import time
from settings import *

orch_container_name = 'orchestartor-docker-test-dynamic'
ps_container_name = 'ps-docker'
master_ps_container_name = 'ps-docker-master'
replica_ps_container_name = 'ps-docker-replica'
network_name = 'orchestrator'

@pytest.fixture(scope='module')
def host():
    subprocess.check_call(['docker', 'network', 'create', network_name])
    orch_docker_id = subprocess.check_output(
        ['docker', 'run', '--name', orch_container_name, '-d', '--network', network_name, docker_image ]).decode().strip()
    time.sleep(20)
    master_ps_docker_id = subprocess.check_output(
        ['docker', 'run', '--name', master_ps_container_name, '-e', 'MYSQL_ROOT_PASSWORD=secret', '-d', '--network', network_name, ps_docker_image,
        '--log-error-verbosity=3', '--report_host="'+master_ps_container_name+'"', '--max-allowed-packet=134217728']).decode().strip()
    time.sleep(20)
    slave_ps_docker_id = subprocess.check_output(
        ['docker', 'run', '--name', replica_ps_container_name, '-d', '--network', network_name, ps_docker_image, 
        '--log-error-verbosity=3', '--report_host="'+replica_ps_container_name+'"', '--max-allowed-packet=134217728']).decode().strip()
    subprocess.check_call(['docker', 'exec', master_ps_docker_id, 'mysql -uroot -psecret -vvv -e"CREATE USER \'repl\'@\'%\' IDENTIFIED WITH mysql_native_password BY \'slavepass\'; GRANT REPLICATION SLAVE ON *.* TO repl@\'%\';"'])
    subprocess.check_call(['docker', 'exec', slave_ps_docker_id, 'mysql -uroot -psecret -e\'change master to master_host="'+master_ps_container_name+'",master_user="repl",master_password="slavepass",master_log_file="binlog.000002";show warnings;\''])
    subprocess.check_call(['docker', 'exec', slave_ps_docker_id, 'mysql -uroot -psecret -e\'START SLAVE;\''])
    # yield testinfra.get_host("docker://root@" + orch_docker_id)
    # subprocess.check_call(['docker', 'rm', '-f', orch_docker_id])

def test_packages(self, host):
    cmd=host.run('echo \'some command\'')
    assert cmd.succeeded