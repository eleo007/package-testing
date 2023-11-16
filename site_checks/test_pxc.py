import os
import requests
import pytest
import json
import re
from packaging import version

PXC_VER_FULL = os.environ.get("PXC_VER_FULL")
DEBUG = os.environ.get("DEBUG")

assert re.search(r'^\d+\.\d+\.\d+-\d+\.\d+$', PXC_VER_FULL)
PXC_VER_PERCONA = '.'.join(PXC_VER_FULL.split('.')[:-1])
PXC_PERCONA_TAG = PXC_VER_FULL.split('.')[-1]
print(PXC_VER_PERCONA)
PXC_VER_UPSTREAM = PXC_VER_FULL.split('-')[0]
print(PXC_VER_FULL)
if version.parse(PXC_VER_UPSTREAM) > version.parse("8.1.0"):
    print("this is 8.1")
    DEB_SOFTWARE_FILES=['buster','bookworm','bullseye', 'bionic','focal', 'jammy']
    RHEL_SOFTWARE_FILES=['redhat/7', 'redhat/8', 'redhat/9']
elif version.parse(PXC_VER_UPSTREAM) > version.parse("8.0.0") and version.parse(PXC_VER_UPSTREAM) < version.parse("8.1.0"):
    print("this is 8.0.0")
    DATA_VERSION='80'
    DEB_SOFTWARE_FILES=['buster','bookworm','bullseye', 'bionic','focal', 'jammy']
    RHEL_SOFTWARE_FILES=['redhat/7', 'redhat/8', 'redhat/9']
elif version.parse(PXC_VER_UPSTREAM) > version.parse("5.7.0") and version.parse(PXC_VER_UPSTREAM) < version.parse("8.0.0"):
    print("this is 5.7")
    DATA_VERSION='57'
    assert os.environ.get("PXC57_INNODB"), "PXC57_INNODB parameter is not defined!"
    PXC57_INNODB=os.environ.get("PXC57_INNODB")
    DEB_SOFTWARE_FILES=['buster','bookworm','bullseye', 'bionic','focal', 'jammy']
    RHEL_SOFTWARE_FILES=['redhat/7', 'redhat/8', 'redhat/9']

SOFTWARE_FILES=DEB_SOFTWARE_FILES+RHEL_SOFTWARE_FILES+['binary','source']

def get_package_tuples():
    list = []
    for software_file in SOFTWARE_FILES:
        data = 'version_files=Percona-XtraDB-Cluster-' + PXC_VER_UPSTREAM + '&software_files=' + software_file
        # print(data)
        req = requests.post("https://www.percona.com/products-api.php",data=data,headers = {"content-type": "application/x-www-form-urlencoded; charset=UTF-8"})
        # print(req)
        assert req.status_code == 200
        # print(req.text)
        assert req.text != '[]', software_file
        print(software_file)
        if software_file == 'binary':
            glibc_versions=["2.17","2.34", "2.35"]
            for glibc_version in glibc_versions:
                if version.parse(PXC_VER_FULL) > version.parse("8.0.0"):
                    print(glibc_version)
                    assert "Percona-XtraDB-Cluster_" + PXC_VER_FULL + "_Linux.x86_64.glibc"+glibc_version+"-minimal.tar.gz" in req.text
                    assert "Percona-XtraDB-Cluster_" + PXC_VER_FULL + "_Linux.x86_64.glibc"+glibc_version+"-minimal.tar.gz.sha256sum" in req.text
                    assert "Percona-XtraDB-Cluster_" + PXC_VER_FULL + "_Linux.x86_64.glibc"+glibc_version+".tar.gz" in req.text
                    assert "Percona-XtraDB-Cluster_" + PXC_VER_FULL + "_Linux.x86_64.glibc"+glibc_version+".tar.gz.sha256sum" in req.text
                elif version.parse(PXC_VER_UPSTREAM) > version.parse("5.7.0") and version.parse(PXC_VER_UPSTREAM) < version.parse("8.0.0"):
                    print(glibc_version)
                    TARBALL_VER=PXC_VER_UPSTREAM + "-rel" + PXC57_INNODB + "-" + PXC_PERCONA_TAG + ".1"
                    print(TARBALL_VER)
                    assert "Percona-XtraDB-Cluster-" + TARBALL_VER + ".Linux.x86_64.glibc"+glibc_version+"-minimal.tar.gz" in req.text
                    assert "Percona-XtraDB-Cluster-" + TARBALL_VER + ".Linux.x86_64.glibc"+glibc_version+"-minimal.tar.gz.sha256sum" in req.text
                    assert "Percona-XtraDB-Cluster-" + TARBALL_VER + ".Linux.x86_64.glibc"+glibc_version+".tar.gz" in req.text
                    assert "Percona-XtraDB-Cluster-" + TARBALL_VER + ".Linux.x86_64.glibc"+glibc_version+".tar.gz.sha256sum" in req.text
        elif software_file == 'source':
            assert "Percona-XtraDB-Cluster-" + PXC_VER_PERCONA + ".tar.gz" in req.text or "Percona-XtraDB-Cluster-" + PXC_VER_FULL + ".tar.gz" in req.text
            assert "Percona-XtraDB-Cluster-" + PXC_VER_PERCONA + ".tar.gz.sha256sum" in req.text or "Percona-XtraDB-Cluster-" + PXC_VER_FULL + ".tar.gz.sha256sum" in req.text
            assert "percona-xtradb-cluster_" + PXC_VER_PERCONA + ".orig.tar.gz" in req.text or "percona-xtradb-cluster-5.7_" + PXC_VER_FULL + ".orig.tar.gz" in req.text
            assert "percona-xtradb-cluster-" + PXC_VER_FULL  + ".generic.src.rpm" in req.text or "Percona-XtraDB-Cluster-57-" + PXC_VER_FULL + ".1.generic.src.rpm" in req.text
        else:
            if version.parse(PXC_VER_FULL) > version.parse("8.0.0"):
                assert "percona-xtradb-cluster-server_" + PXC_VER_UPSTREAM in req.text or "percona-xtradb-cluster-server-" + PXC_VER_UPSTREAM in req.text
                assert "percona-xtradb-cluster-test_" + PXC_VER_UPSTREAM in req.text or "percona-xtradb-cluster-test-" + PXC_VER_UPSTREAM in req.text
                assert "percona-xtradb-cluster-client_" + PXC_VER_UPSTREAM in req.text or "percona-xtradb-cluster-client-" + PXC_VER_UPSTREAM in req.text
                assert "percona-xtradb-cluster-garbd_" + PXC_VER_UPSTREAM in req.text or "percona-xtradb-cluster-garbd-" + PXC_VER_UPSTREAM
                assert "percona-xtradb-cluster_" + PXC_VER_UPSTREAM in req.text or "percona-xtradb-cluster-" + PXC_VER_UPSTREAM in req.text 
                assert "percona-xtradb-cluster-full_" + PXC_VER_UPSTREAM in req.text or "percona-xtradb-cluster-full-" + PXC_VER_UPSTREAM in req.text 
                assert "dbg" in req.text or "debug" in req.text
                if software_file in DEB_SOFTWARE_FILES:
                    assert "libperconaserverclient21-dev_" + PXC_VER_UPSTREAM in req.text
                    assert "libperconaserverclient21_" + PXC_VER_UPSTREAM in req.text
                    assert "percona-xtradb-cluster-source_" + PXC_VER_UPSTREAM in req.text
                    assert "percona-xtradb-cluster-common_" + PXC_VER_UPSTREAM in req.text
                if software_file in RHEL_SOFTWARE_FILES:
                    assert "percona-xtradb-cluster-devel-" + PXC_VER_UPSTREAM in req.text
                    assert "percona-xtradb-cluster-shared-" + PXC_VER_UPSTREAM in req.text
                    assert "percona-xtradb-cluster-icu-data-files-" + PXC_VER_UPSTREAM in req.text
                    if software_file != "redhat/9":
                        assert "percona-xtradb-cluster-shared-compat-" + PXC_VER_UPSTREAM in req.text
            elif version.parse(PXC_VER_UPSTREAM) > version.parse("5.7.0") and version.parse(PXC_VER_UPSTREAM) < version.parse("8.0.0"):
                assert "percona-xtradb-cluster-57_" + PXC_VER_FULL in req.text or "Percona-XtraDB-Cluster-57-" + PXC_VER_FULL in req.text
                assert "percona-xtradb-cluster-server-5.7_" + PXC_VER_FULL in req.text or "Percona-XtraDB-Cluster-server-57-" + PXC_VER_FULL in req.text
                assert "percona-xtradb-cluster-test-5.7_"  + PXC_VER_FULL in req.text or "Percona-XtraDB-Cluster-test-57-" + PXC_VER_FULL in req.text
                assert "percona-xtradb-cluster-client-5.7_" + PXC_VER_FULL in req.text or "Percona-XtraDB-Cluster-client-57-" + PXC_VER_FULL in req.text
                assert "percona-xtradb-cluster-garbd-5.7_" + PXC_VER_FULL in req.text or "Percona-XtraDB-Cluster-garbd-57-" + PXC_VER_FULL in req.text
                assert "percona-xtradb-cluster-full-57_" + PXC_VER_FULL in req.text or "Percona-XtraDB-Cluster-full-57-" + PXC_VER_FULL in req.text
                assert "dbg" in req.text or "debug" in req.text
                if software_file in DEB_SOFTWARE_FILES:
                    assert "libperconaserverclient20-dev_" + PXC_VER_FULL in req.text
                    assert "libperconaserverclient20_" + PXC_VER_FULL in req.text
                    assert "percona-xtradb-cluster-source-5.7_" + PXC_VER_FULL in req.text
                    assert "percona-xtradb-cluster-common-5.7_" + PXC_VER_FULL in req.text
                if software_file in RHEL_SOFTWARE_FILES:
                    assert "Percona-XtraDB-Cluster-devel-57-" + PXC_VER_FULL in req.text
                    assert "Percona-XtraDB-Cluster-shared-57-" + PXC_VER_FULL in req.text
                    if software_file == "redhat/7":
                        assert "Percona-XtraDB-Cluster-shared-compat-57-" + PXC_VER_FULL in req.text

        files = json.loads(req.text)
        for file in files:
            list.append( (software_file,file['filename'],file['link']) )
    return list


LIST_OF_PACKAGES = get_package_tuples()

@pytest.mark.parametrize(('software_file','filename','link'),LIST_OF_PACKAGES)
def test_packages_site(software_file,filename,link):
    print('\nTesting ' + software_file + ', file: ' + filename)
    print(link)
    req = requests.head(link, allow_redirects=True)
    assert req.status_code == 200 and int(req.headers['content-length']) > 0, link
