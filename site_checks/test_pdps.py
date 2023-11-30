# Test website links for Percona Distribution for PS. Tarballs are not built for MySQL Router.

import os
import requests
import pytest
import json
import re
from packaging import version
# PS_VER_FULL="5.7.43-31.1"

PS_VER_FULL="8.0.34-26.1"

# PS_VER_FULL = os.environ.get("PS_VER_FULL")
DEBUG = os.environ.get("DEBUG")

assert re.search(r'^\d+\.\d+\.\d+-\d+\.\d+$', PS_VER_FULL), "PS version is not full. Expected pattern with build: 8.0.34-26.1"

PS_VER = '.'.join(PS_VER_FULL.split('.')[:-1]) #8.0.34-26
print("PS_VER " + PS_VER)
PS_VER_UPSTREAM = PS_VER_FULL.split('-')[0] #8.0.34
print("PS_VER_UPSTREAM " + PS_VER_UPSTREAM)
PS_BUILD_NUM = PS_VER_FULL.split('.')[-1] # "1"
print("PS_BUILD_NUM " + PS_BUILD_NUM)

PT_VER = "3.5.4"
# PS_VER_FULL = os.environ.get("PT_VER")
PXB_VER_FULL = "8.0.34-29.1"
PXB_VER = '.'.join(PXB_VER_FULL.split('.')[:-1]) #8.0.34-26
PXB_MAJOR_VERSION=''.join(PXB_VER_FULL.split('.')[:2])
PXB_BUILD_NUM = PXB_VER_FULL.split('.')[-1]
# PXB_VER = os.environ.get("PXB_VER")
PROXYSQL_VER = "2.5.5"
# PROXYSQL_VER = os.environ.get("PROXYSQL_VER")
ORCH_VER_FULL = "3.2.6-10"
ORCH_VER = ORCH_VER_FULL.split('-')[0]
# ORCH_VER_FULL = os.environ.get("ORCH_VER_FULL")

if version.parse(PS_VER) > version.parse("8.1.0"):
    DEB_SOFTWARE_FILES=['buster', 'bullseye', 'bookworm', 'focal', 'jammy']
    RHEL_SOFTWARE_FILES=['redhat/7', 'redhat/8', 'redhat/9']
elif version.parse(PS_VER) > version.parse("8.0.0") and version.parse(PS_VER) < version.parse("8.1.0"):
    DEB_SOFTWARE_FILES=['buster', 'bullseye', 'bookworm', 'bionic', 'focal', 'jammy']
    RHEL_SOFTWARE_FILES=['redhat/7', 'redhat/8', 'redhat/9']
elif version.parse(PS_VER) > version.parse("5.7.0") and version.parse(PS_VER) < version.parse("8.0.0"):
    assert not version.parse(PS_VER) > version.parse("5.7.0") and version.parse(PS_VER) < version.parse("8.0.0"), "PS 5.7 is not suported"

SOFTWARE_FILES=DEB_SOFTWARE_FILES+RHEL_SOFTWARE_FILES+['binary','source']
# SOFTWARE_FILES=['redhat/8']
RHEL_EL={'redhat/7':'el7', 'redhat/8':'el8', 'redhat/9':'el9'}

def get_package_tuples():
    list = []
    for software_file in SOFTWARE_FILES:
        data = 'version_files=percona-distribution-mysql-ps-' + PS_VER_UPSTREAM + '&software_files=' + software_file
        print(data)
        req = requests.post("https://www.percona.com/products-api.php",data=data,headers = {"content-type": "application/x-www-form-urlencoded; charset=UTF-8"})
        assert req.status_code == 200
        assert req.text != '[]', software_file
        if software_file == 'binary':
            print(f"Loop 1 {software_file}")
            glibc_versions=["2.17","2.27","2.28","2.31","2.34","2.35"]
            for glibc_version in glibc_versions:
                # Check PS tarballs:
                if DEBUG:
                    assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-debug.tar.gz" in req.text
                assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-minimal.tar.gz" in req.text
                assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+".tar.gz" in req.text
                if glibc_version in ['2.34', '2.35'] and version.parse(PS_VER) > version.parse("8.0.0") and version.parse(PS_VER) < version.parse("8.1.0"):
                    assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-zenfs-minimal.tar.gz" in req.text
                    assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-zenfs.tar.gz" in req.text
                # Check mysql-shell tarballs:
                if glibc_version not in ['2.35']:
                    print("Checking mysql-shell")
                    assert "percona-mysql-shell-" + PS_VER_UPSTREAM + "-linux-glibc"+glibc_version+".tar.gz" in req.text
            # Check PT
            assert 'percona-toolkit' + PT_VER + '_x86_64.tar.gz'
            glibc_version="2.17"
            # Check PXB
            assert "percona-xtrabackup-" + PXB_VER+ "-Linux-x86_64.glibc" + glibc_version + "-minimal.tar.gz" in req.text
            assert "percona-xtrabackup-" + PXB_VER+ "-Linux-x86_64.glibc" + glibc_version + ".tar.gz" in req.text
            # Check ProxySQL
            glibc_versions=["2.17","2.23","2.27"]
            for glibc_version in glibc_versions:
                assert 'proxysql-' + PROXYSQL_VER + '-Linux-x86_64.glibc2.17.tar.gz' in req.text

        elif software_file == 'source':
            print(f"Loop 2 {software_file}")
                # Check PS sources:
            assert "percona-server-" + PS_VER + ".tar.gz" in req.text
            assert "percona-server_" + PS_VER  + ".orig.tar.gz" in req.text
            assert "percona-server-" + PS_VER_FULL  + ".generic.src.rpm"
                # Check mysql-shell tarballs:
            assert re.search(rf'percona-mysql-shell_{PS_VER_UPSTREAM}-\d+\.orig\.tar\.gz', req.text)
            assert re.search(rf'percona-mysql-shell-{PS_VER_UPSTREAM}-\d+\.generic\.src\.rpm', req.text)
            assert "percona-mysql-shell-" + PS_VER_UPSTREAM + ".tar.gz" in req.text
                # Check orchestrator tarballs:
            assert "percona-orchestrator-" + ORCH_VER + ".tar.gz"
            assert "percona-orchestrator-" + ORCH_VER_FULL + ".generic.src.rpm"
                # Check Percona Toolkit tarballs:
            assert "percona-toolkit-" + PT_VER + ".tar.gz" in req.text
            assert re.search(rf'percona-toolkit-{PT_VER}-\d+\.src\.rpm', req.text)
                # Check Percona XtraBackup tarballs:
            assert "percona-xtrabackup-" + PXB_VER + ".tar.gz" in req.text
            assert "percona-xtrabackup-" + PXB_MAJOR_VERSION + '_' + PXB_VER  + ".orig.tar.gz" in req.text
            assert "percona-xtrabackup-" + PXB_MAJOR_VERSION + '-' + PXB_VER + '.' + PXB_BUILD_NUM +".generic.src.rpm" in req.text
                # Check proxysql2 tarballs:
            print(f'proxysql2-{PROXYSQL_VER}.tar.gz')
            assert "proxysql2-" + PROXYSQL_VER + ".tar.gz" in req.text
            assert "proxysql2_" + PROXYSQL_VER + ".orig.tar.gz" in req.text
            assert re.search(rf'proxysql2-{PROXYSQL_VER}-\d+\.\d+\.generic\.src\.rpm', req.text)
        
        else:
            if version.parse(PS_VER) > version.parse("8.0.0"):
                print(f"Loop 3 {software_file}")
                if software_file in DEB_SOFTWARE_FILES:
                    PS_DEB_NAME_SUFFIX=PS_VER + "-" + PS_BUILD_NUM + "." + software_file + "_amd64.deb"
                    assert "percona-server-server_" + PS_DEB_NAME_SUFFIX in req.text
                    assert "percona-server-test_" + PS_DEB_NAME_SUFFIX in req.text
                    assert "percona-server-client_" + PS_DEB_NAME_SUFFIX in req.text
                    assert "percona-server-rocksdb_" + PS_DEB_NAME_SUFFIX in req.text
                    assert "percona-mysql-router_" + PS_DEB_NAME_SUFFIX in req.text
                    assert "dbg" in req.text or "debug" in req.text
                    assert "libperconaserverclient21-dev_" + PS_DEB_NAME_SUFFIX in req.text or "libperconaserverclient22-dev_" + PS_DEB_NAME_SUFFIX in req.text
                    assert "libperconaserverclient21_" + PS_DEB_NAME_SUFFIX in req.text or "libperconaserverclient22_" + PS_DEB_NAME_SUFFIX in req.text
                    assert "percona-server-source_" + PS_DEB_NAME_SUFFIX in req.text
                    assert "percona-server-common_" + PS_DEB_NAME_SUFFIX in req.text
                    assert "percona-mysql-shell_" + PS_VER_UPSTREAM in req.text
                    assert "percona-orchestrator-client_" + ORCH_VER in req.text
                    assert "percona-orchestrator-cli_" + ORCH_VER in req.text
                    assert "percona-orchestrator_" + ORCH_VER in req.text
                    assert "percona-toolkit_" + PT_VER in req.text
                    PXB_DEB_NAME_SUFFIX=PXB_MAJOR_VERSION + '_' + PXB_VER + "-" + PXB_BUILD_NUM + "." + software_file + "_amd64.deb"
                    assert "percona-xtrabackup-" + PXB_DEB_NAME_SUFFIX in req.text
                    assert "percona-xtrabackup-dbg-" + PXB_DEB_NAME_SUFFIX in req.text
                    assert "percona-xtrabackup-test-" + PXB_DEB_NAME_SUFFIX in req.text
                    assert "proxysql2_" + PROXYSQL_VER in req.text
                if software_file in RHEL_SOFTWARE_FILES:
                    PS_RPM_NAME_SUFFIX=PS_VER + "." + PS_BUILD_NUM + "." + RHEL_EL[software_file] + ".x86_64.rpm"
                    assert "percona-server-server-" + PS_RPM_NAME_SUFFIX in req.text
                    assert "percona-server-test-" + PS_RPM_NAME_SUFFIX in req.text
                    assert "percona-server-client-" + PS_RPM_NAME_SUFFIX in req.text
                    assert "percona-server-rocksdb-" + PS_RPM_NAME_SUFFIX in req.text
                    assert "percona-mysql-router-" + PS_RPM_NAME_SUFFIX in req.text
                    assert "percona-server-devel-" + PS_RPM_NAME_SUFFIX in req.text
                    assert "percona-server-shared-" + PS_RPM_NAME_SUFFIX in req.text
                    assert "percona-icu-data-files-" + PS_RPM_NAME_SUFFIX in req.text
                    if software_file != "redhat/9":
                        assert "percona-server-shared-compat-" + PS_RPM_NAME_SUFFIX in req.text
                    assert 'percona-mysql-shell-' + PS_VER_UPSTREAM in req.text
                    assert 'percona-orchestrator-' + ORCH_VER in req.text
                    assert 'percona-orchestrator-cli-' + ORCH_VER in req.text
                    assert 'percona-orchestrator-client-' + ORCH_VER in req.text
                    assert 'percona-toolkit-' + PT_VER in req.text
                    PXB_RPM_NAME_SUFFIX='-' + PXB_VER + "." + PXB_BUILD_NUM + "." + RHEL_EL[software_file] + ".x86_64.rpm"
                    assert "percona-xtrabackup-" + PXB_MAJOR_VERSION + PXB_RPM_NAME_SUFFIX in req.text
                    assert "percona-xtrabackup-" + PXB_MAJOR_VERSION + '-debuginfo' + PXB_RPM_NAME_SUFFIX in req.text
                    assert "percona-xtrabackup-test-" + PXB_MAJOR_VERSION + PXB_RPM_NAME_SUFFIX in req.text
                    assert "proxysql2-" + PROXYSQL_VER in req.text
        files = json.loads(req.text)
        for file in files:
            list.append( (software_file,file['filename'],) )
            # list.append( (software_file,file['filename'],file['link']) )
    return list

LIST_OF_PACKAGES = get_package_tuples()
print(*LIST_OF_PACKAGES,sep='\n')
