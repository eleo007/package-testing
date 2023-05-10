#!/usr/bin/env python3
import pytest
import subprocess
import testinfra
import json
import time
from settings import *
import os
import requests

orch_container_name = 'orchestartor-docker-discover'
source_ps_container_name = 'ps-docker-source'
replica_ps_container_name = 'ps-docker-replica'
network_name = 'orchestrator'
ps_password='secret'

source_state_reference = (
    (source_ps_container_name, 'Key', 'Hostname',),(ps_docker_tag, 'Version', ''),
    (replica_ps_container_name,'SlaveHosts', 'Hostname'),
    (True, 'IsLastCheckValid', ''),(True, 'IsUpToDate',''),(7,'SecondsSinceLastSeen','Int64'))

replica_state_reference = (
    (replica_ps_container_name, 'Key', 'Hostname'),(ps_docker_tag, 'Version',''),
    (source_ps_container_name, 'MasterKey', 'Hostname'), 
    (True, 'ReplicationSQLThreadRuning', ''), (True, 'ReplicationIOThreadRuning', ''),  
    (True, 'IsLastCheckValid',''),(True, 'IsUpToDate',''),(7,'SecondsSinceLastSeen','Int64'))

replica_stopped_reference = (
    (replica_ps_container_name, 'Key', 'Hostname'),
    (source_ps_container_name, 'MasterKey', 'Hostname'), 
    (False, 'ReplicationSQLThreadRuning', ''), (False, 'ReplicationIOThreadRuning', ''), 
    (True, 'IsLastCheckValid',''),(True, 'IsUpToDate',''))

def prepare():
        subprocess.check_call(['docker', 'network', 'create', network_name])
        #start orchestrator and PS containers
        subprocess.check_call(['docker', 'run', '--name', orch_container_name, '-d', '--network', network_name, docker_image ])
        time.sleep(10)
        subprocess.check_call(['docker', 'run', '--name', source_ps_container_name, '-e', 'MYSQL_ROOT_PASSWORD='+ps_password+'', '-d', '--network', network_name, ps_docker_image,
            '--log-error-verbosity=3', '--report_host='+source_ps_container_name, '--max-allowed-packet=134217728'])
        time.sleep(10)
        subprocess.check_call(['docker', 'run', '--name', replica_ps_container_name, '-e', 'MYSQL_ROOT_PASSWORD='+ps_password+'', '-d', '--network', network_name, ps_docker_image, 
            '--log-error-verbosity=3', '--report_host='+replica_ps_container_name, '--max-allowed-packet=134217728', '--server-id=2'])
        time.sleep(10)
        #setup replication between PS nodes
        subprocess.check_call(['docker', 'exec', source_ps_container_name, 'mysql', '-uroot', '-p'+ps_password+'', '-e', 'CREATE USER \'repl\'@\'%\' IDENTIFIED WITH mysql_native_password BY \'replicapass\'; GRANT REPLICATION SLAVE ON *.* TO \'repl\'@\'%\';'])
        subprocess.check_call(['docker', 'exec', replica_ps_container_name, 'mysql', '-uroot', '-p'+ps_password+'', '-e', 'CHANGE REPLICATION SOURCE to SOURCE_HOST=\''+source_ps_container_name+'\',SOURCE_USER=\'repl\',SOURCE_PASSWORD=\'replicapass\',SOURCE_LOG_FILE=\'binlog.000002\';START REPLICA;'])
        subprocess.check_call(['docker', 'exec', source_ps_container_name, 'mysql', '-uroot', '-p'+ps_password+'', '-e', 'CREATE USER \'orchestrator\'@\'%\' IDENTIFIED  WITH mysql_native_password BY \'\'; GRANT SUPER, PROCESS, REPLICATION SLAVE, RELOAD ON *.* TO \'orchestrator\'@\'%\'; GRANT SELECT ON mysql.slave_master_info TO \'orchestrator\'@\'%\';'])
        #get orchestrator container IP
        orchestrator_ip = subprocess.check_output(['docker', 'inspect', '-f' '"{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}"', orch_container_name]).decode().strip().replace('"','')
        return orchestrator_ip

orchestrator_ip = prepare()

def run_api_call(command, ps_server):
    server_state = requests.get('http://{}:3000/api/{}/{}/3306'.format(orchestrator_ip, command, ps_server))
    parced_state = json.loads(server_state.text)
    return parced_state

@pytest.fixture(scope='module')
def discover_state():
    discover_state=run_api_call('discover', source_ps_container_name)
    return discover_state

@pytest.fixture(scope='module')
def source_state():
    source_state=run_api_call('instance', source_ps_container_name)
    return source_state

@pytest.fixture(scope='module')
def replica_state():
    time.sleep(10)
    replica_state=run_api_call('instance', replica_ps_container_name)
    print('this is one run')
    return replica_state

@pytest.fixture(scope='module')
def load_state(host):
    source_ps_ip = subprocess.check_output(['docker', 'inspect', '-f' '"{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}"', source_ps_container_name]).decode().strip()
    subprocess.check_call(['docker', 'exec', source_ps_container_name, 'mysql', '-uroot', '-p'+ps_password+'', '-e', \
                           'CREATE USER \'sysbench\'@\'%\' IDENTIFIED  WITH mysql_native_password BY \'Test1234#\'; \
                           GRANT ALL PRIVILEGES on *.* to \'sysbench\'@\'%\'; \
                           CREATE DATABASE sbtest;'])
    cmd='sysbench --tables=20 --table-size=10000 --threads=4 --rand-type=pareto --db-driver=mysql \
        --mysql-user=sysbench --mysql-password=Test1234# --mysql-host={} --mysql-port=3306 --mysql-db=sbtest --mysql-storage-engine=innodb \
        /usr/share/sysbench/oltp_read_write.lua prepare'.format(source_ps_ip)
    host.run(cmd)
    time.sleep(15)
    load_state=run_api_call('instance', replica_ps_container_name)
    return load_state

@pytest.fixture(scope='module')
def replica_stopped_state(host):
    time.sleep(2)
    subprocess.check_call(['docker', 'exec', replica_ps_container_name, 'mysql', '-uroot', '-psecret', '-e', 'STOP REPLICA;'])
    time.sleep(10)
    replica_stopped_state=run_api_call('instance', replica_ps_container_name)
    print('this is one run')
    yield replica_stopped_state
    cmd='docker rm -f $(docker ps -a -q) || true && docker network rm {} || true'.format(network_name)
    host.run(cmd)


def test_discovery(discover_state):
    assert discover_state['Message'] == 'Instance discovered: ps-docker-source:3306', (discover_state['Message'])

@pytest.mark.parametrize("value, key1, key2", source_state_reference, ids=[f'{x[1]} {x[2]}' for x in source_state_reference])
def test_source(source_state, value, key1, key2):
    if key2:
        if key1 == 'SecondsSinceLastSeen':
            assert value > source_state[key1][key2], value
        elif key1 == 'SlaveHosts':
            assert value == source_state[key1][0][key2], value
        else:
            assert value == source_state[key1][key2], value
    else:
        assert value == source_state[key1], value

@pytest.mark.parametrize("value, key1, key2", replica_state_reference, ids=[f'{x[1]} {x[2]}' for x in replica_state_reference])
def test_replica(replica_state, value, key1, key2):
    if key2:
        if key1 == 'SecondsSinceLastSeen': 
            assert value > replica_state[key1][key2], value
        else: 
            assert value == replica_state[key1][key2], value
    else:
        assert value == replica_state[key1], value


@pytest.mark.parametrize("value, key1, key2", replica_state_reference, ids=[f'{x[1]} {x[2]}' for x in replica_state_reference])
def test_load(load_state, value, key1, key2):
    if key2:
        if key1 == 'SecondsSinceLastSeen':
            assert value > load_state[key1][key2], value
        else: # All other cases.
            assert value == load_state[key1][key2], value
    else:
        assert value == load_state[key1], value

@pytest.mark.parametrize("value, key1, key2", replica_stopped_reference, ids=[f'{x[1]} {x[2]}' for x in replica_stopped_reference])
def test_replica_stopped(replica_stopped_state, value, key1, key2):
    if key2:
        if key1 == 'SecondsSinceLastSeen':
            assert value > replica_stopped_state[key1][key2], value
        else:
            assert value == replica_stopped_state[key1][key2], value
    else:
        assert value == replica_stopped_state[key1], value