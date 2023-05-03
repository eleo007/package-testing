#!/usr/bin/env python3
import pytest
import subprocess
import testinfra
import json
import time
from settings import *
import os
import requests

orch_container_name = 'orchestartor-docker-test-dynamic'
source_ps_container_name = 'ps-docker-source'
replica_ps_container_name = 'ps-docker-replica'
network_name = 'orchestrator'
source_state_values = (
    ('Key.Hostname', source_ps_container_name),('Version', ps_docker_tag),('SlaveHosts',replica_ps_container_name),
    ('IsLastCheckValid', 'true'),('IsUpToDate','true'),('SecondsSinceLastSeen.Int64','7'))

@pytest.fixture(scope='module')
def prepare():
    subprocess.check_call(['docker', 'network', 'create', network_name])
    orch_docker_id = subprocess.check_output(
        ['docker', 'run', '--name', orch_container_name, '-d', '--network', network_name, docker_image ]).decode().strip()
    time.sleep(20)
    source_ps_docker_id = subprocess.check_output(
        ['docker', 'run', '--name', source_ps_container_name, '-e', 'MYSQL_ROOT_PASSWORD=secret', '-d', '--network', network_name, ps_docker_image,
        '--log-error-verbosity=3', '--report_host='+source_ps_container_name, '--max-allowed-packet=134217728']).decode().strip()
    time.sleep(20)
    replica_ps_docker_id = subprocess.check_output(
        ['docker', 'run', '--name', replica_ps_container_name, '-e', 'MYSQL_ROOT_PASSWORD=secret', '-d', '--network', network_name, ps_docker_image, 
        '--log-error-verbosity=3', '--report_host='+replica_ps_container_name, '--max-allowed-packet=134217728', '--server-id=2']).decode().strip()
    time.sleep(20)
    subprocess.check_call(['docker', 'exec', source_ps_container_name, 'mysql', '-uroot', '-psecret', '-e', 'CREATE USER \'repl\'@\'%\' IDENTIFIED WITH mysql_native_password BY \'replicapass\'; GRANT REPLICATION SLAVE ON *.* TO \'repl\'@\'%\';'])
    subprocess.check_call(['docker', 'exec', replica_ps_container_name, 'mysql', '-uroot', '-psecret', '-e', 'CHANGE REPLICATION SOURCE to SOURCE_HOST=\''+source_ps_container_name+'\',SOURCE_USER=\'repl\',SOURCE_PASSWORD=\'replicapass\',SOURCE_LOG_FILE=\'binlog.000002\';show warnings;'])
    subprocess.check_call(['docker', 'exec', replica_ps_container_name, 'mysql', '-uroot', '-psecret', '-e', 'START REPLICA;'])
    subprocess.check_call(['docker', 'exec', source_ps_container_name, 'mysql', '-uroot', '-psecret', '-e', 'CREATE USER \'orchestrator\'@\'%\' IDENTIFIED  WITH mysql_native_password BY \'\'; GRANT SUPER, PROCESS, REPLICATION SLAVE, RELOAD ON *.* TO \'orchestrator\'@\'%\'; GRANT SELECT ON mysql.slave_master_info TO \'orchestrator\'@\'%\';'])
    source_ps_ip = subprocess.check_output(['docker', 'inspect', '-f' '"{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}"', source_ps_container_name]).decode().strip()
    orchestrator_ip = subprocess.check_output(['docker', 'inspect', '-f' '"{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}"', orch_container_name]).decode().strip().replace('"','')
    yield orchestrator_ip
#     # yield testinfra.get_host("docker://root@" + orch_docker_id)
#     # subprocess.check_call(['docker', 'rm', '-f', orch_docker_id])
# #curl "http://172.18.0.2:3000/api/discover/172.18.0.3/3306"| jq '.'

# def run_api_query (host, command, filter):
#     orchestrator_ip = subprocess.check_output(['docker', 'inspect', '-f' '"{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}"', orch_container_name]).decode().strip().replace('"','')
#     cmd = host.run('curl -s http://'+orchestrator_ip+':3000/api/'+command+'/'+source_ps_container_name+'/3306| jq -r \'.'+filter+'\'' )
#     assert cmd.succeeded
#     return cmd.stdout

def test_discovery(prepare):
    #prepare.orchestrator_ip = subprocess.check_output(['docker', 'inspect', '-f' '"{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}"', orch_container_name]).decode().strip().replace('"','')
    discover = requests.get('http://{}:3000/api/discover/{}/3306'.format(prepare, source_ps_container_name))
    discover_output = json.loads(discover.text)
    assert discover_output['Message'] == 'Instance discovered: ps-docker-source:3306', (discover_output['Message'])

#curl -s "http://172.18.0.2:3000/api/instance/ps-docker-source/3306"| jq .
# def test_source(host, prepare):
#     cur_state=
#     for value in source_state_values:
#         state = run_api_query(host, 'instance', value[1])
#         if value[0] != 'SecondsSinceLastSeen.Int64':
#             assert value[1] in state, state
#         else:
#             assert state < value[1], (value, state)

# curl -s "http://172.18.0.2:3000/api/instance/ps-docker-replica/3306"| jq .
# def test_replica(host, prepare):
#     message = run_api_query(host,'discover', 'Message')
#     assert message == 'Instance discovered: ps-docker-source:3306', (message)

# curl -s "http://172.18.0.2:3000/api/cluster-info/ps-docker-source" | jq .
# {
#   "ClusterName": "ps-docker-source:3306",
#   "ClusterAlias": ".ps-docker-source",
#   "ClusterDomain": "",
#   "CountInstances": 2,
#   "HeuristicLag": 0,
#   "HasAutomatedMasterRecovery": true,
#   "HasAutomatedIntermediateMasterRecovery": true
# }
# def test_cluster(host, prepare):
#     message = run_api_query(host,'discover', 'Message')
#     assert message == 'Instance discovered: ps-docker-source:3306', (message)

# def test_load(host, prepare):

# def test_slave_stopped(host, prepare):

# def test_replica_bloken