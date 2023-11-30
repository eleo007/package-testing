import os
import requests
import pytest
import json
import re
from packaging import version

PXB_VER_FULL = "2.4.28-1"
# PXB_VER_FULL = "8.0.34-29.1"
# PXB_VER_FULL = "8.1.0-1.1"
# PXB_VER_FULL = os.environ.get("PXB_VER_FULL")
DEBUG = os.environ.get("DEBUG")
PXB_VER_UPSTREAM = PXB_VER_FULL.split('-')[0] # 8.0.34 OR 8.1.0 OR 2.4.28
print("PXB_VER_UPSTREAM " + PXB_VER_UPSTREAM)
MAJOR_VERSION=''.join(PXB_VER_FULL.split('.')[:2])
print("MAJOR_VERSION " +MAJOR_VERSION)

# Validate that full PXB version is passed (with build number): 5.7.43-31.65.1, 8.0.34-29.1; 8.1.0-1.1
if version.parse(PXB_VER_UPSTREAM) > version.parse("8.0.0"):
    assert re.search(r'^\d+\.\d+\.\d+-\d+\.\d+$', PXB_VER_FULL), "PXB 8.0/8.1 version is not full. Pass '8.1.0-1.1' / '8.0.34-26.1'" # 8.1.0-1.1 or  8.0.34-26.1
    PXB_VER = '.'.join(PXB_VER_FULL.split('.')[:-1]) #8.0.34-26
    print("PXB_VER " + PXB_VER)
    PXB_BUILD_NUM = PXB_VER_FULL.split('.')[-1] # "1"
    print("PXB_BUILD_NUM " + PXB_BUILD_NUM)
elif version.parse(PXB_VER_UPSTREAM) > version.parse("2.0.0") and version.parse(PXB_VER_UPSTREAM) < version.parse("8.0.0"):
    print("PXB_VER_UPSTREAM IS OK" + PXB_VER_UPSTREAM)
    PXB_VER = PXB_VER_UPSTREAM #2.4.28-26
    print("PXB_VER " + PXB_VER)
    PXB_BUILD_NUM = PXB_VER_FULL.split('-')[-1] # "1"
    print("PXB_BUILD_NUM " + PXB_BUILD_NUM)
    assert re.search(r'^\d+\.\d+\.\d+-\d+$', PXB_VER_FULL), "PXB 2.4 version is not full.  Pass '2.4.28-1'" # 2.4.28-1


if version.parse(PXB_VER) > version.parse("8.1.0"):
    DEB_SOFTWARE_FILES=['buster', 'bullseye', 'bookworm', 'bionic', 'focal', 'jammy']
    RHEL_SOFTWARE_FILES=['redhat/7', 'redhat/8', 'redhat/9']
elif version.parse(PXB_VER) > version.parse("8.0.0") and version.parse(PXB_VER) < version.parse("8.1.0"):
    DEB_SOFTWARE_FILES=['buster', 'bullseye', 'bookworm', 'bionic', 'focal', 'jammy']
    RHEL_SOFTWARE_FILES=['redhat/7', 'redhat/8', 'redhat/9']
elif version.parse(PXB_VER) > version.parse("2.0.0") and version.parse(PXB_VER) < version.parse("8.0.0"):
    DEB_SOFTWARE_FILES=['stretch', 'buster', 'bullseye', 'xenial', 'bionic', 'focal', 'jammy']
    RHEL_SOFTWARE_FILES=['redhat/7', 'redhat/8', 'redhat/9']

SOFTWARE_FILES=['binary','source']+DEB_SOFTWARE_FILES+RHEL_SOFTWARE_FILES
# SOFTWARE_FILES=RHEL_SOFTWARE_FILES+["binary",'source']
RHEL_EL={'redhat/7':'el7', 'redhat/8':'el8', 'redhat/9':'el9'}

def get_package_tuples():
    list = []
    for software_file in SOFTWARE_FILES:
        data = 'version_files=Percona-XtraBackup-' + PXB_VER + '&software_files=' + software_file
        print(data)
        req = requests.post("https://www.percona.com/products-api.php",data=data,headers = {"content-type": "application/x-www-form-urlencoded; charset=UTF-8"})
        assert req.status_code == 200
        assert req.text != '[]', software_file
        if software_file == 'binary':
            print(f"Loop 1 {software_file}")
            glibc_version="2.17"
            assert "percona-xtrabackup-" + PXB_VER+ "-Linux-x86_64.glibc" + glibc_version + "-minimal.tar.gz" in req.text
            assert "percona-xtrabackup-" + PXB_VER+ "-Linux-x86_64.glibc" + glibc_version + ".tar.gz" in req.text
        elif software_file == 'source':
            print(f"Loop 2 {software_file}")
            assert "percona-xtrabackup-" + PXB_VER + ".tar.gz" in req.text
            assert "percona-xtrabackup-" + MAJOR_VERSION + '_' + PXB_VER  + ".orig.tar.gz" in req.text
            if version.parse(PXB_VER) > version.parse("8.0.0"):
                assert "percona-xtrabackup-" + MAJOR_VERSION + '-' + PXB_VER + '.' + PXB_BUILD_NUM +".generic.src.rpm" in req.text
            elif version.parse(PXB_VER) > version.parse("2.0.0") and version.parse(PXB_VER) < version.parse("8.0.0"):
                assert "percona-xtrabackup-" + MAJOR_VERSION + '-' + PXB_VER + '-' + PXB_BUILD_NUM +".generic.src.rpm"
        else:
            # if version.parse(PXB_VER) > version.parse("8.0.0"):
            print(f"Loop 3 {software_file}")
            if software_file in DEB_SOFTWARE_FILES:
                PXB_DEB_NAME_SUFFIX=MAJOR_VERSION + '_' + PXB_VER + "-" + PXB_BUILD_NUM + "." + software_file + "_amd64.deb"
                assert "percona-xtrabackup-" + PXB_DEB_NAME_SUFFIX in req.text
                assert "percona-xtrabackup-dbg-" + PXB_DEB_NAME_SUFFIX in req.text
                assert "percona-xtrabackup-test-" + PXB_DEB_NAME_SUFFIX in req.text
            elif software_file in RHEL_SOFTWARE_FILES:
                if version.parse(PXB_VER) > version.parse("8.0.0"):
                    PXB_RPM_NAME_SUFFIX='-' + PXB_VER + "." + PXB_BUILD_NUM + "." + RHEL_EL[software_file] + ".x86_64.rpm"
                elif version.parse(PXB_VER) > version.parse("2.0.0") and version.parse(PXB_VER) < version.parse("8.0.0"):
                    PXB_RPM_NAME_SUFFIX='-' + PXB_VER + "-" + PXB_BUILD_NUM + "." + RHEL_EL[software_file] + ".x86_64.rpm"
                assert "percona-xtrabackup-" + MAJOR_VERSION + PXB_RPM_NAME_SUFFIX in req.text
                assert "percona-xtrabackup-" + MAJOR_VERSION + '-debuginfo' + PXB_RPM_NAME_SUFFIX in req.text
                assert "percona-xtrabackup-test-" + MAJOR_VERSION + PXB_RPM_NAME_SUFFIX in req.text

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