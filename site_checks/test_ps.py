import os
import requests
import pytest
import json
import re
from packaging import version

# PS_VER_FULL = "8.0.34-26.1"
PS_VER_FULL = os.environ.get("PS_VER_FULL")
DEBUG = os.environ.get("DEBUG")

assert re.search(r'^\d+\.\d+\.\d+-\d+\.\d+$', PS_VER_FULL)

PS_VER = '.'.join(PS_VER_FULL.split('.')[:-1])
print(PS_VER)
if version.parse(PS_VER) > version.parse("8.1.0"):
    print("this is 8.1")
    DEB_SOFTWARE_FILES=['buster','bookworm','bullseye', 'bionic','focal', 'jammy']
    RHEL_SOFTWARE_FILES=['redhat/7', 'redhat/8', 'redhat/9']
elif version.parse(PS_VER) > version.parse("8.0.0") and version.parse(PS_VER) < version.parse("8.1.0"):
    print("this is 8.0.1")
    DEB_SOFTWARE_FILES=['buster','bookworm','bullseye', 'bionic','focal', 'jammy']
    RHEL_SOFTWARE_FILES=['redhat/7', 'redhat/8', 'redhat/9']
elif version.parse(PS_VER) > version.parse("5.7.0") and version.parse(PS_VER) < version.parse("8.0.0"):
    print("this is 5.7")
    DEB_SOFTWARE_FILES=['buster','bookworm','bullseye', 'bionic','focal', 'jammy']
    RHEL_SOFTWARE_FILES=['redhat/7', 'redhat/8', 'redhat/9']

SOFTWARE_FILES=DEB_SOFTWARE_FILES+RHEL_SOFTWARE_FILES+['binary','source']

def get_package_tuples():
    list = []
    for software_file in SOFTWARE_FILES:
        data = 'version_files=Percona-Server-' + PS_VER + '&software_files=' + software_file
        # print(data)
        req = requests.post("https://www.percona.com/products-api.php",data=data,headers = {"content-type": "application/x-www-form-urlencoded; charset=UTF-8"})
        # print(req)
        assert req.status_code == 200
        # print(req.text)
        assert req.text != '[]', software_file
        print(software_file)
        if software_file == 'binary':
            if version.parse(PS_VER) < version.parse("8.0.0"):
                glibc_versions=["2.17","2.35"]
            else:
                glibc_versions=["2.17","2.27","2.28","2.31","2.34","2.35"]
            for glibc_version in glibc_versions:
                if DEBUG:
                    print("Checking debug")
                    assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-debug.tar.gz" in req.text
                    assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-debug.tar.gz.sha256sum" in req.text
                assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-minimal.tar.gz" in req.text
                assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+"-minimal.tar.gz.sha256sum" in req.text
                assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+".tar.gz" in req.text
                assert "Percona-Server-" + PS_VER + "-Linux.x86_64.glibc"+glibc_version+".tar.gz.sha256sum" in req.text
        elif software_file == 'source':
            assert "percona-server-" + PS_VER + ".tar.gz" in req.text
            assert "percona-server-" + PS_VER  + ".tar.gz.sha256sum" in req.text
            assert "percona-server_" + PS_VER  + ".orig.tar.gz" in req.text or "percona-server-5.7_" + PS_VER  + ".orig.tar.gz" in req.text
        else:
            if version.parse(PS_VER) > version.parse("8.0.0"):
                assert "percona-server-server_" + PS_VER in req.text or "percona-server-server-" + PS_VER in req.text
                assert "percona-server-test_" + PS_VER in req.text or "percona-server-test-" + PS_VER in req.text
                assert "percona-server-client_" + PS_VER in req.text or "percona-server-client-" + PS_VER in req.text
                assert "percona-server-rocksdb_" + PS_VER in req.text or "percona-server-rocksdb-" + PS_VER in req.text
                assert "percona-mysql-router_" + PS_VER in req.text or "percona-mysql-router-" + PS_VER
                assert "dbg" in req.text or "debug" in req.text
                if software_file in DEB_SOFTWARE_FILES:
                    assert "libperconaserverclient21-dev_" + PS_VER in req.text
                    assert "libperconaserverclient21_" + PS_VER in req.text
                    assert "percona-server-source_" + PS_VER in req.text
                    assert "percona-server-common_" + PS_VER in req.text or "percona-server-common-" + PS_VER in req.text
                if software_file in RHEL_SOFTWARE_FILES:
                    assert "percona-server-devel-" + PS_VER in req.text
                    assert "percona-server-shared-" + PS_VER in req.text
                    if software_file != "redhat/9":
                        assert "percona-server-shared-compat-" + PS_VER in req.text
            elif version.parse(PS_VER) > version.parse("5.7.0") and version.parse(PS_VER) < version.parse("8.0.0"):
                assert "percona-server-server-5.7_" + PS_VER in req.text or "Percona-Server-server-57-" + PS_VER in req.text
                assert "percona-server-test-5.7_"  + PS_VER in req.text or "Percona-Server-test-57-" + PS_VER in req.text
                assert "percona-server-client-5.7_" + PS_VER in req.text or "Percona-Server-client-57-" + PS_VER in req.text
                assert "percona-server-rocksdb-5.7_" + PS_VER in req.text or "Percona-Server-rocksdb-57-" + PS_VER in req.text
                assert "percona-server-tokudb-5.7_" + PS_VER in req.text or "Percona-Server-tokudb-57-" + PS_VER in req.text
                assert "dbg" in req.text or "debug" in req.text
                if software_file in DEB_SOFTWARE_FILES:
                    assert "libperconaserverclient20-dev_" + PS_VER in req.text
                    assert "libperconaserverclient20_" + PS_VER in req.text
                    assert "percona-server-source-5.7_" + PS_VER in req.text
                    assert "percona-server-common-5.7_" + PS_VER in req.text
                if software_file in RHEL_SOFTWARE_FILES:
                    assert "Percona-Server-devel-57-" + PS_VER in req.text
                    assert "Percona-Server-shared-57-" + PS_VER in req.text
                    if software_file != "redhat/9":
                        assert "Percona-Server-shared-compat-57-" + PS_VER in req.text

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
