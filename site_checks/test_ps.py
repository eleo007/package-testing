import os
import requests
import pytest
import json
import re
from packaging import version

PS_VER_FULL = os.environ.get("PS_VER_FULL")
DEBUG = os.environ.get("DEBUG")

assert re.search(r'^\d+\.\d+\.\d+-\d+\.\d+$', PS_VER_FULL), "PS version is not full. Expected pattern with build: 8.0.34-26.1"

PS_VER = '.'.join(PS_VER_FULL.split('.')[:-1]) #8.0.34-26
print(PS_VER)
PS_BUILD_NUM = PS_VER_FULL.split('.')[-1] # "1"
print(PS_BUILD_NUM)

if version.parse(PS_VER) > version.parse("8.1.0"):
    DEB_SOFTWARE_FILES=['buster', 'bullseye', 'bookworm', 'focal', 'jammy']
    RHEL_SOFTWARE_FILES=['redhat/7', 'redhat/8', 'redhat/9']
elif version.parse(PS_VER) > version.parse("8.0.0") and version.parse(PS_VER) < version.parse("8.1.0"):
    DEB_SOFTWARE_FILES=['buster', 'bullseye', 'bookworm', 'bionic', 'focal', 'jammy']
    RHEL_SOFTWARE_FILES=['redhat/7', 'redhat/8', 'redhat/9']
elif version.parse(PS_VER) > version.parse("5.7.0") and version.parse(PS_VER) < version.parse("8.0.0"):
    DEB_SOFTWARE_FILES=['buster', 'bullseye', 'bookworm', 'bionic', 'focal', 'jammy']
    RHEL_SOFTWARE_FILES=['redhat/7', 'redhat/8', 'redhat/9']

SOFTWARE_FILES=DEB_SOFTWARE_FILES+RHEL_SOFTWARE_FILES+['binary','source']
RHEL_EL={'redhat/7':'el7', 'redhat/8':'el8', 'redhat/9':'el9'}

def get_package_tuples():
    list = []
    for software_file in SOFTWARE_FILES:
        data = 'version_files=Percona-Server-' + PS_VER + '&software_files=' + software_file
        req = requests.post("https://www.percona.com/products-api.php",data=data,headers = {"content-type": "application/x-www-form-urlencoded; charset=UTF-8"})
        assert req.status_code == 200
        assert req.text != '[]', software_file
        if software_file == 'binary':
            print(f"Loop 1 {software_file}")
            if version.parse(PS_VER) < version.parse("8.0.0"):
                glibc_versions=["2.17","2.35"]
            else:
                glibc_versions=["2.17","2.27","2.28","2.31","2.34","2.35"]
            for glibc_version in glibc_versions:
                if DEBUG:
                    assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-debug.tar.gz" in req.text
                    assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-debug.tar.gz.sha256sum" in req.text
                assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-minimal.tar.gz" in req.text
                assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-minimal.tar.gz.sha256sum" in req.text
                assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+".tar.gz" in req.text
                assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+".tar.gz.sha256sum" in req.text
                if glibc_version in ['2.34', '2.35'] and version.parse(PS_VER) > version.parse("8.0.0") and version.parse(PS_VER) < version.parse("8.1.0"):
                    assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-zenfs-minimal.tar.gz" in req.text
                    assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-zenfs-minimal.tar.gz.sha256sum" in req.text
                    assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-zenfs.tar.gz" in req.text
                    assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-zenfs.tar.gz.sha256sum" in req.text
        elif software_file == 'source':
            print(f"Loop 2 {software_file}")
            assert "percona-server-" + PS_VER + ".tar.gz" in req.text
            assert "percona-server-" + PS_VER  + ".tar.gz.sha256sum" in req.text
            assert "percona-server_" + PS_VER  + ".orig.tar.gz" in req.text or "percona-server-5.7_" + PS_VER  + ".orig.tar.gz" in req.text
            assert "percona-server-" + PS_VER_FULL  + ".generic.src.rpm" in req.text or "Percona-Server-57-" + PS_VER_FULL + ".generic.src.rpm" in req.text
        else:
            if version.parse(PS_VER) > version.parse("8.0.0"):
                print(f"Loop 3 {software_file}")
                if software_file in DEB_SOFTWARE_FILES:
                    DEB_NAME_SUFFIX=PS_VER + "-" + PS_BUILD_NUM + "." + software_file + "_amd64.deb"
                    assert "percona-server-server_" + DEB_NAME_SUFFIX in req.text
                    assert "percona-server-test_" + DEB_NAME_SUFFIX in req.text
                    assert "percona-server-client_" + DEB_NAME_SUFFIX in req.text
                    assert "percona-server-rocksdb_" + DEB_NAME_SUFFIX in req.text
                    assert "percona-mysql-router_" + DEB_NAME_SUFFIX in req.text
                    assert "dbg" in req.text or "debug" in req.text
                    assert "libperconaserverclient21-dev_" + DEB_NAME_SUFFIX in req.text or "libperconaserverclient22-dev_" + DEB_NAME_SUFFIX in req.text
                    assert "libperconaserverclient21_" + DEB_NAME_SUFFIX in req.text or "libperconaserverclient22_" + DEB_NAME_SUFFIX in req.text
                    assert "percona-server-source_" + DEB_NAME_SUFFIX in req.text
                    assert "percona-server-common_" + DEB_NAME_SUFFIX in req.text
                if software_file in RHEL_SOFTWARE_FILES:
                    RPM_NAME_SUFFIX=PS_VER + "." + PS_BUILD_NUM + "." + RHEL_EL[software_file] + ".x86_64.rpm"
                    assert "percona-server-server-" + RPM_NAME_SUFFIX in req.text
                    assert "percona-server-test-" + RPM_NAME_SUFFIX in req.text
                    assert "percona-server-client-" + RPM_NAME_SUFFIX in req.text
                    assert "percona-server-rocksdb-" + RPM_NAME_SUFFIX in req.text
                    assert "percona-mysql-router-" + RPM_NAME_SUFFIX in req.text
                    assert "percona-server-devel-" + RPM_NAME_SUFFIX in req.text
                    assert "percona-server-shared-" + RPM_NAME_SUFFIX in req.text
                    assert "percona-icu-data-files-" + RPM_NAME_SUFFIX in req.text
                    if software_file != "redhat/9":
                        assert "percona-server-shared-compat-" + RPM_NAME_SUFFIX in req.text
            elif version.parse(PS_VER) > version.parse("5.7.0") and version.parse(PS_VER) < version.parse("8.0.0"):
                print(f"Loop 3 {software_file}")
                if software_file in DEB_SOFTWARE_FILES:
                    DEB_NAME_SUFFIX=PS_VER + "-" + PS_BUILD_NUM + "." + software_file + "_amd64.deb"
                    assert "percona-server-server-5.7_" + DEB_NAME_SUFFIX in req.text
                    assert "percona-server-test-5.7_"  + DEB_NAME_SUFFIX in req.text
                    assert "percona-server-client-5.7_" + DEB_NAME_SUFFIX in req.text
                    assert "percona-server-rocksdb-5.7_" + DEB_NAME_SUFFIX in req.text
                    assert "percona-server-tokudb-5.7_" + DEB_NAME_SUFFIX in req.text
                    assert "dbg" in req.text or "debug" in req.text
                    assert "libperconaserverclient20-dev_" + DEB_NAME_SUFFIX in req.text
                    assert "libperconaserverclient20_" + DEB_NAME_SUFFIX in req.text
                    assert "percona-server-source-5.7_" + DEB_NAME_SUFFIX in req.text
                    assert "percona-server-common-5.7_" + DEB_NAME_SUFFIX in req.text
                if software_file in RHEL_SOFTWARE_FILES:
                    RPM_NAME_SUFFIX=PS_VER + "." + PS_BUILD_NUM + "." + RHEL_EL[software_file] + ".x86_64.rpm"
                    assert "Percona-Server-server-57-" + RPM_NAME_SUFFIX in req.text
                    assert "Percona-Server-test-57-" + RPM_NAME_SUFFIX in req.text
                    assert "Percona-Server-client-57-" + RPM_NAME_SUFFIX in req.text
                    assert "Percona-Server-rocksdb-57-" + RPM_NAME_SUFFIX in req.text
                    assert "Percona-Server-tokudb-57-" + RPM_NAME_SUFFIX in req.text
                    assert "Percona-Server-devel-57-" + RPM_NAME_SUFFIX in req.text
                    assert "Percona-Server-shared-57-" + RPM_NAME_SUFFIX in req.text
                    if software_file != "redhat/9":
                        assert "Percona-Server-shared-compat-57-" + RPM_NAME_SUFFIX in req.text

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
