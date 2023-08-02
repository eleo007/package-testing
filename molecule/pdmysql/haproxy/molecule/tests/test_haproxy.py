import os
import time

import pytest
import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')

VERSION = os.getenv("VERSION")


@pytest.fixture
def create_user(host):
    with host.sudo("root"):
        cmd = "mysql -e \"CREATE USER 'clustercheckuser'@'%' IDENTIFIED WITH mysql_native_password by 'clustercheckpassword!';\
            GRANT PROCESS ON *.* TO 'clustercheckuser'@'%';\
            CREATE USER 'haproxy_user'@'%' IDENTIFIED WITH mysql_native_password by '$3Kr$t';\""
        result = host.run(cmd)
        assert result.rc == 0, result.stdout
        cmd = 'service xinetd restart'
        result = host.run(cmd)
        assert result.rc == 0, result.stdout
        cmd = 'service haproxy restart'
        result = host.run(cmd)
        assert result.rc == 0, result.stdout
        time.sleep(5)

def test_haproxy_service(host):
    assert host.service("haproxy").is_running

def test_haproxy_clustercheck(host, create_user):
    with host.sudo("root"):
        cmd = "/usr/bin/clustercheck"
        result = host.run(cmd)
        assert result.rc == 0, result.stdout
        assert 'Percona XtraDB Cluster Node is synced.' in result.stdout, result.stdout

def test_haproxy_connect(host):
    with host.sudo("root"):
        cmd = "mysql -e \"SELECT VERSION();\""
        result = host.run(cmd)
        assert result.rc == 0, result.stdout
        cmd = "mysql --port=9201 -h127.0.0.1 -uhaproxy_user -p$3Kr$t -e \"SELECT VERSION();\" "
        for wait in range(1,120):
            result = host.run(cmd)
            if "ERROR 2013 (HY000): Lost connection to MySQL server at 'reading initial communication packet', system error: 0" in result.stdout:
                time.sleep(1)
                wait+=1
        else:
            result = host.run(cmd)
            assert 'my_verify_string' in result.stdout, result.stdout
