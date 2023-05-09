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

source_state_check = (
    (source_ps_container_name, 'Key', 'Hostname',),(ps_docker_tag, 'Version', ''),(replica_ps_container_name,'SlaveHosts', 'Hostname'),
    (True, 'IsLastCheckValid', ''),(True, 'IsUpToDate',''),(7,'SecondsSinceLastSeen','Int64'))

replica_state_check = ((replica_ps_container_name, 'Key', 'Hostname'),(ps_docker_tag, 'Version',''),
    (source_ps_container_name, 'MasterKey', 'Hostname'), (False, 'IsDetachedMaster', ''), (True, 'Slave_SQL_Running','' ), 
    (True, 'ReplicationSQLThreadRuning', ''), (True, 'Slave_IO_Running', ''), (True, 'ReplicationIOThreadRuning', ''), (1, 'ReplicationSQLThreadState', ''),
    (1, 'ReplicationIOThreadState', ''), (0 ,'SecondsBehindMaster', 'Int64'), (0, 'SlaveLagSeconds', 'Int64'), (0, 'ReplicationLagSeconds', 'Int64'), 
    (True, 'IsLastCheckValid',''),(True, 'IsUpToDate',''),(7,'SecondsSinceLastSeen','Int64'))

replica_state_stopped = ((replica_ps_container_name, 'Key', 'Hostname'),(ps_docker_tag, 'Version',''),
    (source_ps_container_name, 'MasterKey', 'Hostname'), (False, 'IsDetachedMaster', ''), (False, 'Slave_SQL_Running','' ), 
    (False, 'ReplicationSQLThreadRuning', ''), (False, 'Slave_IO_Running', ''), (False, 'ReplicationIOThreadRuning', ''), (0, 'ReplicationSQLThreadState', ''),
    (0, 'ReplicationIOThreadState', ''), (0 ,'SecondsBehindMaster', 'Int64'), (0, 'SlaveLagSeconds', 'Int64'), (0, 'ReplicationLagSeconds', 'Int64'), 
    (True, 'IsLastCheckValid',''),(True, 'IsUpToDate',''))

class Orchestrator:
    def __init__(self):
        subprocess.check_call(['docker', 'network', 'create', network_name])
        orch_docker_id = subprocess.check_output(
            ['docker', 'run', '--name', orch_container_name, '-d', '--network', network_name, docker_image ]).decode().strip()
        time.sleep(10)
        source_ps_docker_id = subprocess.check_output(
            ['docker', 'run', '--name', source_ps_container_name, '-e', 'MYSQL_ROOT_PASSWORD=secret', '-d', '--network', network_name, ps_docker_image,
            '--log-error-verbosity=3', '--report_host='+source_ps_container_name, '--max-allowed-packet=134217728']).decode().strip()
        time.sleep(10)
        replica_ps_docker_id = subprocess.check_output(
            ['docker', 'run', '--name', replica_ps_container_name, '-e', 'MYSQL_ROOT_PASSWORD=secret', '-d', '--network', network_name, ps_docker_image, 
            '--log-error-verbosity=3', '--report_host='+replica_ps_container_name, '--max-allowed-packet=134217728', '--server-id=2']).decode().strip()
        time.sleep(10)
        subprocess.check_call(['docker', 'exec', source_ps_container_name, 'mysql', '-uroot', '-psecret', '-e', 'CREATE USER \'repl\'@\'%\' IDENTIFIED WITH mysql_native_password BY \'replicapass\'; GRANT REPLICATION SLAVE ON *.* TO \'repl\'@\'%\';'])
        subprocess.check_call(['docker', 'exec', replica_ps_container_name, 'mysql', '-uroot', '-psecret', '-e', 'CHANGE REPLICATION SOURCE to SOURCE_HOST=\''+source_ps_container_name+'\',SOURCE_USER=\'repl\',SOURCE_PASSWORD=\'replicapass\',SOURCE_LOG_FILE=\'binlog.000002\';show warnings;'])
        subprocess.check_call(['docker', 'exec', replica_ps_container_name, 'mysql', '-uroot', '-psecret', '-e', 'START REPLICA;'])
        subprocess.check_call(['docker', 'exec', source_ps_container_name, 'mysql', '-uroot', '-psecret', '-e', 'CREATE USER \'orchestrator\'@\'%\' IDENTIFIED  WITH mysql_native_password BY \'\'; GRANT SUPER, PROCESS, REPLICATION SLAVE, RELOAD ON *.* TO \'orchestrator\'@\'%\'; GRANT SELECT ON mysql.slave_master_info TO \'orchestrator\'@\'%\';'])
        source_ps_ip = subprocess.check_output(['docker', 'inspect', '-f' '"{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}"', source_ps_container_name]).decode().strip()
        self.orchestrator_ip = subprocess.check_output(['docker', 'inspect', '-f' '"{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}"', orch_container_name]).decode().strip().replace('"','')
#     # yield testinfra.get_host("docker://root@" + orch_docker_id)
#     # subprocess.check_call(['docker', 'rm', '-f', orch_docker_id])
# #curl "http://172.18.0.2:3000/api/discover/172.18.0.3/3306"| jq '.'

    def run_api_call(self, command, ps_server):
        server_state = requests.get('http://{}:3000/api/{}/{}/3306'.format(self.orchestrator_ip, command, ps_server))
        parced_state = json.loads(server_state.text)
        return parced_state
    
@pytest.fixture(scope='module')
def discover_state():
    orchestrator=Orchestrator()
    # orchestrator.prepare()
    discover_state=orchestrator.run_api_call('discover', source_ps_container_name)
    return discover_state

@pytest.fixture(scope='module')
def source_state():
    orchestrator=Orchestrator()
    source_state=orchestrator.run_api_call('instance', source_ps_container_name)
    return source_state

@pytest.fixture(scope='module')
def replica_state():
    time.sleep(10)
    orchestrator=Orchestrator()
    replica_state=orchestrator.run_api_call('instance', replica_ps_container_name)
    print('this is one run')
    return replica_state

@pytest.fixture(scope='module')
def replica_stopped_state():
    orchestrator=Orchestrator()
    subprocess.check_call(['docker', 'exec', replica_ps_container_name, 'mysql', '-uroot', '-psecret', '-e', 'STOP REPLICA;'])
    time.sleep(5)
    replica_stopped_state=orchestrator.run_api_call('instance', replica_ps_container_name)
    print('this is one run')
    return replica_stopped_state

class TestOrchestrator:
    def test_discovery(self, discover_state):
        assert discover_state['Message'] == 'Instance discovered: ps-docker-source:3306', (discover_state['Message'])

    #curl -s "http://172.18.0.2:3000/api/instance/ps-docker-source/3306"| jq .
    @pytest.mark.parametrize("value, key1, key2", source_state_check)
    def test_source(self, source_state, value, key1, key2):
    #    for value in source_state_check:
        if key2:
            if key1 == 'SecondsSinceLastSeen': # Lastseen is int and should be less than 7 sec
                assert value > source_state[key1][key2], value
            elif key1 == 'SlaveHosts': # SlaveHosts returns list of objects. In testcase we have 1 replica == 1 object thus we check the 1st object in the list
                assert value == source_state[key1][0][key2], value
            else: # All other cases.
                assert value == source_state[key1][key2], value
        elif not key2:
            assert value == source_state[key1], value
        else:
            print('Incorrect input in the variable!')

    # curl -s "http://172.18.0.2:3000/api/instance/ps-docker-replica/3306"| jq .
    @pytest.mark.parametrize("value, key1, key2", replica_state_check)
    def test_replica(self, replica_state, value, key1, key2):
        if key2:
            if key1 == 'SecondsSinceLastSeen': # Lastseen is int and should be less than 7 sec
                assert value > replica_state[key1][key2], value
            elif key1 == 'SlaveHosts': # SlaveHosts returns list of objects. In testcase we have 1 replica == 1 object thus we check the 1st object in the list
                assert value == replica_state[key1][0][key2], value
            else: # All other cases.
                assert value == replica_state[key1][key2], value
        elif not key2:
            assert value == replica_state[key1], value
        else:
            print('Incorrect input in the variable!')

    @pytest.mark.parametrize("value, key1, key2", replica_state_stopped)
    def test_replica_stopped(self, replica_stopped_state, value, key1, key2):
        if key2:
            if key1 == 'SecondsSinceLastSeen': # Lastseen is int and should be less than 7 sec
                assert value > replica_stopped_state[key1][key2], value
            elif key1 == 'SlaveHosts': # SlaveHosts returns list of objects. In testcase we have 1 replica == 1 object thus we check the 1st object in the list
                assert value == replica_stopped_state[key1][0][key2], value
            else: # All other cases.
                assert value == replica_stopped_state[key1][key2], value
        elif not key2:
            assert value == replica_stopped_state[key1], value
        else:
            print('Incorrect input in the variable!')

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

    # def test_replica_broken