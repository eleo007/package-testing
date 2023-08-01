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
        cmd = "mysql -e \"CREATE USER 'clustercheckuser'@'%' IDENTIFIED WITH mysql_native_password by 'clustercheckpassword!';GRANT PROCESS ON *.* TO 'clustercheckuser'@'%';\""
        result = host.run(cmd)
        assert result.rc == 0, result.stdout
        cmd = 'service xinetd restart'
        result = host.run(cmd)
        assert result.rc == 0, result.stdout
        cmd = 'service haproxy restart'
        result = host.run(cmd)
        assert result.rc == 0, result.stdout
        time.sleep(60) 

def test_haproxy_service(host):
    assert host.service("haproxy").is_running


def test_haproxy(host, create_user):
    with host.sudo("root"):
        cmd = "mysql -e \"SELECT VERSION();\""
        result = host.run(cmd)
        assert result.rc == 0, result.stdout
        cmd = "mysql --port=9201 -h127.0.0.1 -e \"SELECT VERSION();\" "
        result = host.run(cmd)
        print(result.stdout)
        assert result.rc == 0, result.stdout
