#!/usr/bin/env python3
import pytest
import subprocess
import testinfra
import time
import os
#from settings import *

orch_version = os.getenv('OCHESTARTOR_VERSION')
container_name = 'orchestartor-docker-test-static'

docker_acc = os.getenv('DOCKER_ACC')
orch_tag = os.getenv('ORCHESTRATOR_TAG')

docker_product = 'percona-orchestrator'
docker_tag = orch_tag
docker_image = docker_acc + "/" + docker_product + ":" + docker_tag

@pytest.fixture(scope='module')
def host():
    docker_id = subprocess.check_output(
        ['docker', 'run', '--name', container_name, '-d', docker_image ]).decode().strip()
    subprocess.check_call(['docker','exec','--user','root',container_name,'microdnf','install','net-tools'])
    time.sleep(20)
    yield testinfra.get_host("docker://root@" + docker_id)
    subprocess.check_call(['docker', 'rm', '-f', docker_id])


class TestMysqlEnvironment:
    def test_packages(self, host):
        pkg_name = "percona-orchestrator"
        assert host.package(pkg_name).is_installed
        assert orch_version in host.package(pkg_name).version +'-'+host.package(pkg_name).release, host.package(pkg_name).version+'-'+host.package(pkg_name).release

    #@pytest.mark.parametrize("binary", orch_binary)
    def test_binaries_exist(self, host):
        orch_binary="/usr/local/orchestrator/orchestrator"
        assert host.file(orch_binary).exists
        assert oct(host.file(orch_binary).mode) == '0o755'

    def test_binaries_version(self, host):
        assert orch_version in host.check_output("/usr/local/orchestrator/orchestrator --version")


    def test_process_running(self, host):
        process = host.process.filter(comm="orchestrator")
        assert process in 'abababbaab'

    def test_mysql_port_3000(self, host):
        assert host.socket('tcp://127.0.0.1:3000').is_listening

    def test_mysql_port_10008(self, host):
        assert host.socket('tcp://127.0.0.1:10008').is_listening

    def test_mysql_user(self, host):
        assert host.user('mysql').exists
        assert host.user('mysql').uid == 1001
        assert host.user('mysql').gid == 1001
        assert 'mysql' in host.user('mysql').groups

    def test_mysql_group(self, host):
        assert host.group('mysql').exists
        assert host.group('mysql').gid == 1001

    def test_orch_permissions(self, host):
        assert host.file('/var/lib/orchestrator').user == 'mysql'
        assert host.file('/var/lib/orchestrator').group == 'mysql'
        assert oct(host.file('/var/lib/orchestrator').mode) == '0o755'

    def test_mysql_files_permissions(self, host):
        assert host.file('/etc/orchestrator').user == 'root'
        assert host.file('/etc/orchestrator').group == 'root'
        assert oct(host.file('/etc/orchestrator').mode) == '0o755'