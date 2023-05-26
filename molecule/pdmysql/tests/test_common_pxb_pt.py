import os
import pytest
import testinfra.utils.ansible_runner
from .settings import *

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')

DEBPACKAGES = ['percona-xtrabackup-80',
               'percona-xtrabackup-test-80',
               'percona-xtrabackup-dbg-80']

RPMPACKAGES = ['percona-xtrabackup-80',
               'percona-xtrabackup-test-80',
               'percona-xtrabackup-80-debuginfo']

PTBINS = ['pt-align', 'pt-archiver', 'pt-config-diff', 'pt-deadlock-logger', 'pt-diskstats',
          'pt-duplicate-key-checker', 'pt-fifo-split', 'pt-find', 'pt-fingerprint',
          'pt-fk-error-logger', 'pt-heartbeat', 'pt-index-usage', 'pt-ioprofile', 'pt-kill',
          'pt-mext', 'pt-mongodb-query-digest', 'pt-mongodb-summary', 'pt-mysql-summary',
          'pt-online-schema-change', 'pt-pmp', 'pt-query-digest', 'pt-show-grants', 'pt-sift',
          'pt-slave-delay', 'pt-slave-find', 'pt-slave-restart', 'pt-stalk', 'pt-summary',
          'pt-table-checksum', 'pt-table-sync', 'pt-table-usage', 'pt-upgrade',
          'pt-variable-advisor', 'pt-visual-explain']

PXB_VERSION = os.getenv("PXB_VERSION")
DEB_PERCONA_BUILD_PXB_VERSION = ''
RPM_PERCONA_BUILD_PXB_VERSION = ''
if re.search(r'^\d+\.\d+\.\d+-\d+\.\d+$', PXB_VERSION): # if full package PXB_VERSION 8.0.32-25.1 is passed
    DEB_PERCONA_BUILD_PXB_VERSION = re.sub(r'.(\d+)$',r'-\g<1>', PXB_VERSION) # 8.0.32-24-2
    RPM_PERCONA_BUILD_PXB_VERSION = PXB_VERSION # 8.0.32-24.2
    PXB_VERSION = '.'.join(PXB_VERSION.split('.')[:-1]) # 8.0.32-24

PT_VERSION = os.getenv("PT_VERSION")

@pytest.mark.parametrize("package", DEBPACKAGES)
def test_check_deb_package(host, package):
    dist = host.system_info.distribution
    if dist.lower() in RHEL_DISTS:
        pytest.skip("This test only for RHEL based platforms")
    pkg = host.package(package)
    assert pkg.is_installed
    if DEB_PERCONA_BUILD_PXB_VERSION:
        assert DEB_PERCONA_BUILD_PXB_VERSION in pkg.version, pkg.version
    else:
        assert PXB_VERSION in pkg.version, pkg.version

@pytest.mark.parametrize("package", RPMPACKAGES)
def test_check_rpm_package(host, package):
    dist = host.system_info.distribution
    if dist.lower() in DEB_DISTS:
        pytest.skip("This test only for RHEL based platforms")
    pkg = host.package(package)
    assert pkg.is_installed
    if RPM_PERCONA_BUILD_PXB_VERSION:
        assert RPM_PERCONA_BUILD_PXB_VERSION in pkg.version+'-'+pkg.release, pkg.version+'-'+pkg.release
    else:
        assert PXB_VERSION in pkg.version+'-'+pkg.release, pkg.version+'-'+pkg.release

def test_binary_version(host):
    cmd = "xtrabackup --version"
    result = host.run(cmd)
    assert result.rc == 0, result.stderr
    assert PXB_VERSION in result.stderr, (result.stdout, result.stdout)


@pytest.mark.parametrize("pt_bin", PTBINS)
def test_pt_binaries(host, pt_bin):
    cmd = '{} --version'.format(pt_bin)
    result = host.run(cmd)
    assert PT_VERSION in result.stdout, result.stdout

@pytest.mark.install
def test_sources_pxb_version(host):
    if REPO == "testing" or REPO == "experimental":
        pytest.skip("This test only for main repo")
    dist = host.system_info.distribution
    if dist.lower() in RHEL_DISTS:
        pytest.skip("This test only for DEB distributions")
    if DEB_PERCONA_BUILD_PXB_VERSION:
        cmd = "apt-cache madison percona-xtrabackup-80 | grep Source | grep \"{}\"".format(DEB_PERCONA_BUILD_PXB_VERSION)
    else:
        cmd = "apt-cache madison percona-xtrabackup-80 | grep Source | grep \"{}\"".format(PXB_VERSION)
    result = host.run(cmd)
    assert result.rc == 0, (result.stderr, result.stdout)
    assert PXB_VERSION in result.stdout, result.stdout

@pytest.mark.install
def test_sources_pt_version(host):
    if REPO == "testing" or REPO == "experimental":
        pytest.skip("This test only for main repo")
    dist = host.system_info.distribution
    if dist.lower() in RHEL_DISTS:
        pytest.skip("This test only for DEB distributions")
    cmd = "apt-cache madison percona-toolkit | grep Source | grep \"{}\"".format(PT_VERSION)
    result = host.run(cmd)
    assert result.rc == 0, (result.stderr, result.stdout)
    assert PT_VERSION in result.stdout, result.stdout
