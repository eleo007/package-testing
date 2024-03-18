#!/usr/bin/env python3
import pytest
import subprocess
import testinfra
import time
from packaging import version
import os
import stat

import testinfra.utils.ansible_runner
testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')

@pytest.fixture(scope='module')
def test_load_env_vars_define_in_test(host):
    # base_dir = os.getenv('BASE_DIR')
    # ps_version = os.getenv('PS_VERSION')
    # ps_revision = os.getenv('PS_REVISION')
    # fips_supported = os.getenv('FIPS_SUPPORTED')
    # pro = os.getenv('PRO')
    # print(base_dir, ps_version, ps_revision, fips_supported, pro)
    with host.sudo():
        vars={'BASE_DIR':os.getenv('BASE_DIR'),'PS_VERSION':os.getenv('PS_VERSION'),'PS_REVISION':os.getenv('PS_REVISION'),'PRO':os.getenv('PRO'),'FIPS_SUPPORTED':os.getenv('FIPS_SUPPORTED')}
        # vars={'BASE_DIR':pro,'PS_REVISION':ps_version}
        for var, value in vars.items():
            cmd=f"echo {var}={value} >> /etc/environment"
            host.run(cmd)
    cmd="groups $USER| awk -F' ' '{print $1$2$3}'"
    user_group=host.run(cmd).stdout.replace(" ", "").replace("\n","")
    with host.sudo():
        for dir in (f'./package-testing',os.getenv('BASE_DIR')):
            cmd=f"chown -R {user_group} {dir}"
            host.check_output(cmd)
            cmd=f"ls -l {dir}"
            host.run(cmd)
    # cmd = f"export PS_VERSION={os.getenv('FIPS_SUPPORTED')} && export PS_REVISION={os.getenv('PS_REVISION')} && export PRO={pro} && export FIPS_SUPPORTED={fips_supported} && export BASE_DIR={base_dir}"


def test_bats(host, test_load_env_vars_define_in_test):
    cmd = "./package-testing/binary-tarball-tests/ps/run.sh"
# with host.sudo():
    result = host.run(cmd)
    print(result.stdout)
    print(result.stderr)
    assert result.rc == 0, result.stdout