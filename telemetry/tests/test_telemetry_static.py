#!/usr/bin/env python3
import pytest
import os
import json
from packaging import version

# VERSION=os.environ.get("TA_VERSION")
# REVISION=os.environ.get("TA_REVISION")

PAK_VERSION = '0.1-1'
VERSION = 'phase-0.1'
REVISION = '13b74807'

RHEL_DISTS = ["redhat", "centos", "rhel", "oracleserver", "ol", "amzn"]

DEB_DISTS = ["debian", "ubuntu"]

os.environ['PERCONA_TELEMETRY_URL'] = 'https://check.percona.com/v1/telemetry/GenericReport'

telemetry_log_file="/var/log/percona/telemetry-agent.log"
# telemetry_log_file="/home/eleonora/telemetry.log"

pillars_list=["ps", "pg", "psmdb"]

# Dictionary of default values that TA should start with
telemetry_defaults=[["RootPath", "/usr/local/percona/telemetry"],["PSMetricsPath", "/usr/local/percona/telemetry/ps"],
         ["PSMDBMetricsPath", "/usr/local/percona/telemetry/psmdb"],["PXCMetricsPath", "/usr/local/percona/telemetry/pxc"],
        ["PGMetricsPath", "/usr/local/percona/telemetry/pg"], ["HistoryPath", "/usr/local/percona/telemetry/history"],
        ["CheckInterval", 86400], ["HistoryKeepInterval", 604800]
    ]

platform_defaults=[["ResendTimeout", 60], ["URL","https://check.percona.com/v1/telemetry/GenericReport"]
    ]

telem_root_dir = '/usr/local/percona/telemetry/'

telem_history_dir=telem_root_dir + 'history/'


##################################################################################
#################################### TESTS #######################################
##################################################################################


def test_ta_package(host):
    dist = host.system_info.distribution
    pkg = host.package("percona-telemetry-agent")
    assert pkg.is_installed
    if dist.lower() in DEB_DISTS:
        assert PAK_VERSION in pkg.version, pkg.version
    else:
        assert PAK_VERSION in pkg.version+'-'+pkg.release, pkg.version+'-'+pkg.release

def test_ta_service(host):
    ta_serv = host.service("percona-telemetry-agent")
    assert ta_serv.is_running
    assert ta_serv.is_enabled
    assert ta_serv.systemd_properties["User"] == 'daemon'
    assert ta_serv.systemd_properties["Group"] == 'percona-telemetry'
    assert "percona-telemetry-agent" in ta_serv.systemd_properties["EnvironmentFilesoup"]

def test_ta_dirs(host):
    assert host.file('/usr/local/percona').group == 'percona-telemetry'
    assert oct(host.file('/usr/local/percona').mode) == '0o775'
    assert host.file(telem_root_dir).is_directory
    assert host.file(telem_root_dir).user == 'daemon'
    assert host.file(telem_root_dir).group == 'percona-telemetry'
    assert oct(host.file(telem_root_dir).mode) == '0o755'
    assert host.file(telem_history_dir).is_directory
    assert host.file(telem_history_dir).user == 'daemon'
    assert host.file(telem_root_dir).group == 'percona-telemetry'
    assert oct(host.file(telem_history_dir).mode) == '0o6755'

def test_ta_log_file(host):
    assert host.file(telemetry_log_file).is_file
    assert host.file("/var/log/percona/telemetry-agent-error.log").is_file

def test_ta_rotation(host):
    rotate_file_content = host.file("/etc/logrotate.d/percona-telemetry-agent").content_string
    assert("/var/log/percona/telemetry-agent*.log") in rotate_file_content
    assert 'weekly' in rotate_file_content
    assert 'rotate 4' in rotate_file_content
    assert 'compress' in rotate_file_content
    assert 'dateext' in rotate_file_content
    assert 'notifempty' in rotate_file_content
    assert 'copytruncate' in rotate_file_content

@pytest.mark.parametrize("ta_key, ref_value", telemetry_defaults)
def test_ta_telemetry_default_values(host, ta_key, ref_value):
    log_file_params = host.file(telemetry_log_file).content_string.partition('\n')[0]
    cur_values=json.loads(log_file_params)
    telem_config=cur_values["config"]["Telemetry"]
    assert len(telem_config) == 8
    assert telem_config[ta_key] == ref_value

@pytest.mark.parametrize("ta_key, ref_value", platform_defaults)
def test_ta_platform_default_values(host, ta_key, ref_value):
    log_file_params = host.file(telemetry_log_file).content_string.partition('\n')[0]
    cur_values=json.loads(log_file_params)
    platform_config=cur_values["config"]["Platform"]
    assert len(platform_config) == 2
    assert platform_config[ta_key] == ref_value

def test_ta_version(host):
    cmd = "/usr/bin/percona-telemetry-agent --version"
    result = host.run(cmd)
    assert VERSION in result.stdout, result.stdout
    assert REVISION in result.stdout, result.stdout

def test_ta_defaults_file(host):
    dist = host.system_info.distribution
    if dist.lower() in DEB_DISTS:
        options_file = '/etc/default/percona-telemetry-agent'
    else:
        options_file = '/etc/sysconfig/percona-telemetry-agent'
    defaults_file_content = host.file(options_file).content_string
    assert 'PERCONA_TELEMETRY_CHECK_INTERVAL' in defaults_file_content
    assert 'PERCONA_TELEMETRY_HISTORY_KEEP_INTERVAL' in defaults_file_content
    assert 'PERCONA_TELEMETRY_RESEND_INTERVAL' in defaults_file_content
    assert 'PERCONA_TELEMETRY_UR' in defaults_file_content
