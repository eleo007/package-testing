#!/usr/bin/env python3
import pytest
import subprocess
import testinfra
import json
import time
from settings import *
import os
import requests

orch_container = 'orchestartor-docker-discover'
source_ps_container = 'ps-docker-source'
replica_ps_container = 'ps-docker-replica'
network_name = 'orchestrator'
ps_password='secret'

source_attr_reference = ({"key_path": ["Key", "Hostname"], "expected_value": source_ps_container},
                         {"key_path": ["Version"], "expected_value": ps_docker_tag},
                         {"key_path": ["SlaveHosts", "Hostname"], "expected_value": replica_ps_container},
                         {"key_path": ["IsLastCheckValid"], "expected_value": True},
                         {"key_path": ["IsUpToDate"], "expected_value": True},)

replica_attr_reference = ({"key_path": ["Key", "Hostname"], "expected_value": replica_ps_container},
                          {"key_path": ["Version"], "expected_value": ps_docker_tag},
                          {"key_path": ["MasterKey", "Hostname"], "expected_value": source_ps_container},
                          {"key_path": ["ReplicationSQLThreadRuning"], "expected_value": True},
                          {"key_path": ["ReplicationIOThreadRuning"], "expected_value": True},
                          {"key_path": ["IsLastCheckValid"], "expected_value": True},
                          {"key_path": ["IsUpToDate"], "expected_value": True},)

replica_stopped_attr_reference = ({"key_path": ["Key", "Hostname"], "expected_value": replica_ps_container},
                                  {"key_path": ["MasterKey", "Hostname"], "expected_value": source_ps_container},
                                  {"key_path": ["ReplicationSQLThreadRuning"], "expected_value": False},
                                  {"key_path": ["ReplicationIOThreadRuning"], "expected_value": False},
                                  {"key_path": ["IsLastCheckValid"], "expected_value": True},
                                  {"key_path": ["IsUpToDate"], "expected_value": True},)

@pytest.fixture(scope='module', autouse=True)
def orchestrator_ip(host):
        subprocess.check_call(['docker', 'network', 'create', network_name])
        #start orchestrator and PS containers
        subprocess.check_call(['docker', 'run', '--name', orch_container, '-d', '--network', network_name, docker_image ])
        time.sleep(10)
        subprocess.check_call(['docker', 'run', '--name', source_ps_container, '-e', 'MYSQL_ROOT_PASSWORD='+ps_password+'', '-d', '--network', network_name, ps_docker_image,
            '--log-error-verbosity=3', '--report_host='+source_ps_container, '--max-allowed-packet=134217728'])
        time.sleep(10)
        subprocess.check_call(['docker', 'run', '--name', replica_ps_container, '-e', 'MYSQL_ROOT_PASSWORD='+ps_password+'', '-d', '--network', network_name, ps_docker_image, 
            '--log-error-verbosity=3', '--report_host='+replica_ps_container, '--max-allowed-packet=134217728', '--server-id=2'])
        time.sleep(10)
        #setup replication between PS nodes
        subprocess.check_call(['docker', 'exec', source_ps_container, 'mysql', '-uroot', '-p'+ps_password+'', '-e', 'CREATE USER \'repl\'@\'%\' IDENTIFIED WITH mysql_native_password BY \'replicapass\'; GRANT REPLICATION SLAVE ON *.* TO \'repl\'@\'%\';'])
        subprocess.check_call(['docker', 'exec', replica_ps_container, 'mysql', '-uroot', '-p'+ps_password+'', '-e', 'CHANGE REPLICATION SOURCE to SOURCE_HOST=\''+source_ps_container+'\',SOURCE_USER=\'repl\',SOURCE_PASSWORD=\'replicapass\',SOURCE_LOG_FILE=\'binlog.000002\';START REPLICA;'])
        subprocess.check_call(['docker', 'exec', source_ps_container, 'mysql', '-uroot', '-p'+ps_password+'', '-e', 'CREATE USER \'orchestrator\'@\'%\' IDENTIFIED  WITH mysql_native_password BY \'\'; GRANT SUPER, PROCESS, REPLICATION SLAVE, RELOAD ON *.* TO \'orchestrator\'@\'%\'; GRANT SELECT ON mysql.slave_master_info TO \'orchestrator\'@\'%\';'])
        subprocess.check_call(['docker', 'exec', source_ps_container, 'mysql', '-uroot', '-p'+ps_password+'', '-e', \
                            'CREATE USER \'sysbench\'@\'%\' IDENTIFIED  WITH mysql_native_password BY \'Test1234#\'; \
                            GRANT ALL PRIVILEGES on *.* to \'sysbench\'@\'%\'; \
                            CREATE DATABASE sbtest;'])
            #get orchestrator container IP
        orchestrator = subprocess.check_output(['docker', 'inspect', '-f' '"{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}"', orch_container]).decode().strip().replace('"','')
        yield orchestrator
        cmd='docker rm -f $(docker ps -a -q) || true && docker network rm {} || true'.format(network_name)
        host.run(cmd)

def receive_current_value(key_path, server_state):
    if len(key_path) == 2:
        if key_path[0] == 'SlaveHosts':
            current_value = server_state[key_path[0]][0][key_path[1]]
            return current_value
        else:
            current_value = server_state[key_path[0]][key_path[1]]
            return current_value
    else:
        current_value = server_state[key_path[0]]
        return current_value

def test_discovery(orchestrator_ip):
    r=requests.get('http://{}:3000/api/{}/{}/3306'.format(orchestrator_ip, 'discover', source_ps_container))
    discover_state = json.loads(r.text)
    assert r.status_code == 200
    assert discover_state['Message'] == 'Instance discovered: ps-docker-source:3306', (discover_state['Message'])

def test_source(orchestrator_ip):
    r=requests.get('http://{}:3000/api/{}/{}/3306'.format(orchestrator_ip, 'instance', source_ps_container))
    source_state = json.loads(r.text)
    assert r.status_code == 200
    for value in source_attr_reference:
        current_attr_value = receive_current_value(value['key_path'], source_state)
        print(current_attr_value)
        assert current_attr_value == value['expected_value'], value

def test_replica(orchestrator_ip):
    time.sleep(10)
    r=requests.get('http://{}:3000/api/{}/{}/3306'.format(orchestrator_ip, 'instance', replica_ps_container))
    source_state = json.loads(r.text)
    assert r.status_code == 200
    for value in replica_attr_reference:
        current_attr_value = receive_current_value(value['key_path'], source_state)
        print(current_attr_value)
        assert current_attr_value == value['expected_value'], value

def test_load(host,orchestrator_ip):
    source_ps_ip = subprocess.check_output(['docker', 'inspect', '-f' '"{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}"', source_ps_container]).decode().strip()
    cmd='sysbench --tables=20 --table-size=10000 --threads=4 --rand-type=pareto --db-driver=mysql \
        --mysql-user=sysbench --mysql-password=Test1234# --mysql-host={} --mysql-port=3306 --mysql-db=sbtest --mysql-storage-engine=innodb \
        /usr/share/sysbench/oltp_read_write.lua prepare'.format(source_ps_ip)
    host.run(cmd)
    time.sleep(15)
    r=requests.get('http://{}:3000/api/{}/{}/3306'.format(orchestrator_ip, 'instance', replica_ps_container))
    source_state = json.loads(r.text)
    assert r.status_code == 200
    for value in replica_attr_reference:
        current_attr_value = receive_current_value(value['key_path'], source_state)
        print(current_attr_value)
        assert current_attr_value == value['expected_value'], value

def test_replica_stopped(orchestrator_ip):
    time.sleep(2)
    subprocess.check_call(['docker', 'exec', replica_ps_container, 'mysql', '-uroot', '-psecret', '-e', 'STOP REPLICA;'])
    time.sleep(10)
    r=requests.get('http://{}:3000/api/{}/{}/3306'.format(orchestrator_ip, 'instance', replica_ps_container))
    source_state = json.loads(r.text)
    assert r.status_code == 200
    for value in replica_stopped_attr_reference:
        current_attr_value = receive_current_value(value['key_path'], source_state)
        print(current_attr_value)
        assert current_attr_value == value['expected_value'], value