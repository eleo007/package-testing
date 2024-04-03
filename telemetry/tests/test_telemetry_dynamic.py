#!/usr/bin/env python3
import pytest
import subprocess
import testinfra
import time
import os
import json
import shutil
import mysql
from packaging import version

# from settings import *
os.environ['PERCONA_TELEMETRY_URL'] = 'https://check-dev.percona.com/v1/telemetry/GenericReport'
# os.environ['PERCONA_TELEMETRY_CHECK_INTERVAL'] = '10'
# TEL_URL_VAR="PERCONA_TELEMETRY_URL=https://check-dev.percona.com/v1/telemetry/GenericReport"

#### !!!!!!!!!!!!!!! CHANGE URL TO CORRECT ONE AFTER THE CHANGES!!!!!!!!!!!
telemetry_defaults=[["RootPath", "/usr/local/percona/telemetry"],["PSMetricsPath", "/usr/local/percona/telemetry/ps"],
         ["PSMDBMetricsPath", "/usr/local/percona/telemetry/psmdb"],["PXCMetricsPath", "/usr/local/percona/telemetry/pxc"],
        ["PGMetricsPath", "/usr/local/percona/telemetry/pg"], ["HistoryPath", "/usr/local/percona/telemetry/history"],
        ["CheckInterval", 86400], ["HistoryKeepInterval", 604800]
    ]

platform_defaults=[["ResendTimeout", 60], ["URL","https://check-dev.percona.com/v1/telemetry/GenericReport"]
    ]

@pytest.fixture(scope="module")
def get_defaults(host):
# awk -F'values from config:' '{print $2}'  ~/telemetry.lo | head -n1
    host.run("timeout 2 ~/telemetry-agent/bin/telemetry-agent > ~/telemetry.log")
    cmd="head -n1 ~/telemetry.log"
    output=host.run(cmd)
    # os.unsetenv('PERCONA_TELEMETRY_URL')
    # cmd="./output.sh"
    # output=host.run(cmd)
    y=json.loads(output.stdout)
    return y

@pytest.mark.parametrize("key, value", telemetry_defaults)
def test_telemetry_default_values(host, get_defaults, key, value):
    cur_values=get_defaults
    telem_config=cur_values["config"]["Telemetry"]
    assert len(telem_config) == 8
    assert telem_config[key] == value

@pytest.mark.parametrize("key, value", platform_defaults)
def test_platform_default_values(host, get_defaults, key, value):
    cur_values=get_defaults
    platform_config=cur_values["config"]["Platform"]
    assert len(platform_config) == 2
    assert platform_config[key] == value

