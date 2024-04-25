#!/usr/bin/env python3
import pytest
import subprocess
import testinfra
import time
import os
import json
import shutil
import re
import mysql
from packaging import version

VERSION=os.environ.get("TA_VERSION")
REVISION=os.environ.get("TA_REVISION")

RHEL_DISTS = ["redhat", "centos", "rhel", "oracleserver", "ol", "amzn"]

DEB_DISTS = ["debian", "ubuntu"]

# from settings import *
os.environ['PERCONA_TELEMETRY_URL'] = 'https://check-dev.percona.com/v1/telemetry/GenericReport'
# os.environ['PERCONA_TELEMETRY_CHECK_INTERVAL'] = '10'
# TEL_URL_VAR="PERCONA_TELEMETRY_URL=https://check-dev.percona.com/v1/telemetry/GenericReport"

deployment = 'PACKAGE'

telemetry_log_file="/var/log/percona/telemetry-agent.log"
# telemetry_log_file="/home/eleonora/telemetry.log"



pillars_list=["ps", "pg", "psmdb"]

#### !!!!!!!!!!!!!!! CHANGE URL TO CORRECT ONE AFTER THE CHANGES!!!!!!!!!!!
# Dictionary of default values that TA should start with
telemetry_defaults=[["RootPath", "/usr/local/percona/telemetry"],["PSMetricsPath", "/usr/local/percona/telemetry/ps"],
         ["PSMDBMetricsPath", "/usr/local/percona/telemetry/psmdb"],["PXCMetricsPath", "/usr/local/percona/telemetry/pxc"],
        ["PGMetricsPath", "/usr/local/percona/telemetry/pg"], ["HistoryPath", "/usr/local/percona/telemetry/history"],
        ["CheckInterval", 86400], ["HistoryKeepInterval", 604800]
    ]

platform_defaults=[["ResendTimeout", 60], ["URL","https://check-dev.percona.com/v1/telemetry/GenericReport"]
    ]

telem_root_dir = '/usr/local/percona/telemetry/'

telem_history_dir=telem_root_dir + 'history/'


##################################################################################
#################################### TESTS #######################################
##################################################################################


def test_ta_package(host):
    pkg = host.package("percona-telemry-agent")
    assert pkg.is_installed
    assert VERSION in pkg.version

def test_ta_service(host):
    ta_serv = host.service("percona-telemry-agent")
    assert ta_serv.is_running
    assert ta_serv.is_enabled

def test_ta_dirs(host):
    assert host.file(telem_root_dir).is_directory
    assert host.file(telem_root_dir).user == 'root'
    assert host.file(telem_root_dir).mode == '0o755'
    assert host.file(telem_history_dir).is_directory
    assert host.file(telem_history_dir).user == 'root'
    assert host.file(telem_history_dir).mode == '0o755'

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
def test_ta_telemetry_default_values(host, get_ta_defaults, ta_key, ref_value):
    cur_values=get_ta_defaults
    telem_config=cur_values["config"]["Telemetry"]
    assert len(telem_config) == 8
    assert telem_config[ta_key] == ref_value

@pytest.mark.parametrize("ta_key, ref_value", platform_defaults)
def test_ta_platform_default_values(host, get_ta_defaults, ta_key, ref_value):
    cur_values=get_ta_defaults
    platform_config=cur_values["config"]["Platform"]
    assert len(platform_config) == 2
    assert platform_config[ta_key] == ref_value


def test_ta_version(host):
    cmd = "/usr/bin/percona-telemetry-agent --version"
    result = host.run(cmd)
    assert VERSION in result.stdout, result.stdout
    assert REVISION in result.stdout, result.stdout
