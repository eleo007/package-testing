#!/usr/bin/env python3
import pytest
import subprocess
import testinfra
import time
import shlex
from settings import *


class PxcNode:
    def __init__(self, node_name, bootstrap_node=False):
        self.node_name = node_name
        self.bootstrap_node = bootstrap_node
        if bootstrap_node:
            self.docker_id = subprocess.check_output(
                ['docker', 'run', '--name', node_name, '-e', 'MYSQL_ROOT_PASSWORD='+pxc_pwd, 
                 '-e', 'CLUSTER_NAME='+cluster_name, '--net='+docker_network,'-d', docker_image]).decode().strip()
            time.sleep(120)
            if pxc_version_major == "8.0":
                subprocess.check_call(['mkdir', '-p', test_pwd+'/cert'])
                subprocess.check_call(['chown', 'vagrant:vagrant', test_pwd+'/cert'])
                subprocess.check_call(['docker', 'cp', node_name+':/var/lib/mysql/ca.pem', test_pwd+'/cert'])
                subprocess.check_call(['docker', 'cp', node_name+':/var/lib/mysql/server-cert.pem', test_pwd+'/cert'])
                subprocess.check_call(['docker', 'cp', node_name+':/var/lib/mysql/server-key.pem', test_pwd+'/cert'])
                subprocess.check_call(['docker', 'cp', node_name+':/var/lib/mysql/client-cert.pem', test_pwd+'/cert'])
                subprocess.check_call(['docker', 'cp', node_name+':/var/lib/mysql/client-key.pem', test_pwd+'/cert'])
                subprocess.check_call(['chmod','-R','a+r', test_pwd+'/cert'])
        else:
            if pxc_version_major == "8.0":
                self.docker_id = subprocess.check_output(
                ['docker', 'run', '--name', node_name, '-e', 'MYSQL_ROOT_PASSWORD='+pxc_pwd,
                '-e', 'CLUSTER_NAME='+cluster_name, '-e', 'CLUSTER_JOIN='+base_node_name+'1',
                '--net='+docker_network,'-v', test_pwd+'/config:/etc/percona-xtradb-cluster.conf.d',
                '-v', test_pwd+'/cert:/cert', '-d', docker_image]).decode().strip()
            else:
                self.docker_id = subprocess.check_output(
                ['docker', 'run', '--name', node_name, '-e', 'MYSQL_ROOT_PASSWORD='+pxc_pwd,
                '-e', 'CLUSTER_NAME='+cluster_name, '-e', 'CLUSTER_JOIN='+base_node_name+'1',
                '--net='+docker_network, '-d', docker_image]).decode().strip()
        self.ti_host = testinfra.get_host("docker://root@" + self.docker_id)

    def destroy(self):
        subprocess.check_call(['docker', 'rm', '-f', self.docker_id])
        if self.bootstrap_node:
            subprocess.check_call(['rm', '-rf', test_pwd+'/cert'])

    def run_query(self, query):
        cmd = self.ti_host.run('mysql --user=root --password='+pxc_pwd+' -S/tmp/mysql.sock -s -N -e ' + shlex.quote(query))
        assert cmd.succeeded
        return cmd.stdout

@pytest.fixture(scope='module')
def cluster():
    cluster = []
    subprocess.check_call(['docker', 'pull', docker_image])
    subprocess.check_call(['docker', 'network', 'create', docker_network])
    node1 = PxcNode(base_node_name+'1',True)
    cluster.append(node1)
    node2 = PxcNode(base_node_name+'2',False)
    cluster.append(node2)
    node3 = PxcNode(base_node_name+'3',False)
    cluster.append(node3)
    time.sleep(40)
    yield cluster
    for node in cluster:
        node.destroy()
    subprocess.check_call(['docker', 'network', 'rm', docker_network])

class GardbNode:
    def run_docker(self):
        self.garbd_docker_image = "redhat/ubi8"
        subprocess.check_call(['docker', 'pull', self.garbd_docker_image])
#        subprocess.check_call(['docker', 'network', 'create', 'garbd_network'])
        self.docker_id = subprocess.check_output(['docker', 'run', '-d', '-i', '--name=garbd', '--net='+docker_network, '-v', test_pwd+'/cert:/cert', self.garbd_docker_image]).decode().strip()

    def install_garbd(self):
        if pxc_version_major == "8.0":
            self.repo_name = 'pxc-80'
            self.garbd_name = 'percona-xtradb-cluster-garbd-8.0.26-16.1.el8'
#            self.garbd_name = 'percona-xtradb-cluster-garbd'
        else:
            self.repo_name = 'pxc-57'
            self.garbd_name = 'Percona-XtraDB-Cluster-garbd-57'
        subprocess.check_call(['docker', 'exec', 'garbd', 'yum', 'install', '-y', 'https://repo.percona.com/yum/percona-release-latest.noarch.rpm'])
        subprocess.check_call(['docker', 'exec', 'garbd', 'percona-release', 'enable', self.repo_name])
        subprocess.check_call(['docker', 'exec', 'garbd', 'rpm', '--import', 'https://repo.percona.com/yum/RPM-GPG-KEY-Percona'])
        subprocess.check_call(['docker', 'exec', 'garbd', 'rpm', '--import', 'https://repo.percona.com/yum/PERCONA-PACKAGING-KEY'])
# OLDER VERSION OF PACKAGE:
        subprocess.check_call(['docker', 'exec', 'garbd', 'yum', 'install', '-y', self.garbd_name]) 

    def connect_pxc(self):
        self.pxc_ips = subprocess.check_output(['docker', 'inspect', '-f' '"{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}"', base_node_name+'1', base_node_name+'2',base_node_name+'3']).decode().strip().replace('\n',',').replace('"','')
        subprocess.check_call(['docker', 'exec', '-d', 'garbd', 'garbd', '--group='+cluster_name, '--address=gcomm://'+self.pxc_ips, '--option="socket.ssl_key=/cert/server-key.pem; socket.ssl_cert=/cert/server-cert.pem; socket.ssl_ca=/cert/ca.pem; socket.ssl_cipher=AES128-SHA256"'])

    def destroy(self):
        subprocess.check_call(['docker', 'rm', '-f', self.docker_id])
 
@pytest.fixture(scope='module')
def garbd():
    start_docker = GardbNode()
    start_docker.run_docker()
    start_docker.install_garbd()
    time.sleep(5)
    start_docker.connect_pxc()
    time.sleep(30)
    yield start_docker
    start_docker.destroy()

#class TestGardb:
def test_cluster_size(cluster,garbd):
    output = cluster[0].run_query('SHOW STATUS LIKE "wsrep_cluster_size";')
    assert output.split('\t')[1].strip() == "4"

def test_second_cluster_size(cluster, garbd):
    time.sleep(60)
    output = cluster[0].run_query('SHOW STATUS LIKE "wsrep_cluster_size";')
    assert output.split('\t')[1].strip() == "4"