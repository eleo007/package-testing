#!/usr/bin/env python3
import pytest
import subprocess
import testinfra
import time
import os
import json
import shutil
import shutil
import mysql
from packaging import version

# from settings import *
os.environ['PERCONA_TELEMETRY_URL'] = 'https://check-dev.percona.com/v1/telemetry/GenericReport'
# os.environ['PERCONA_TELEMETRY_CHECK_INTERVAL'] = '10'
# TEL_URL_VAR="PERCONA_TELEMETRY_URL=https://check-dev.percona.com/v1/telemetry/GenericReport"

telemetry_log_file="/home/eleonora/telemetry.log"

pillars_list=["ps", "pg", "psmdb"]

#### !!!!!!!!!!!!!!! CHANGE URL TO CORRECT ONE AFTER THE CHANGES!!!!!!!!!!!
telemetry_defaults=[["RootPath", "/usr/local/percona/telemetry"],["PSMetricsPath", "/usr/local/percona/telemetry/ps"],
         ["PSMDBMetricsPath", "/usr/local/percona/telemetry/psmdb"],["PXCMetricsPath", "/usr/local/percona/telemetry/pxc"],
        ["PGMetricsPath", "/usr/local/percona/telemetry/pg"], ["HistoryPath", "/usr/local/percona/telemetry/history"],
        ["CheckInterval", 86400], ["HistoryKeepInterval", 604800]
    ]

platform_defaults=[["ResendTimeout", 60], ["URL","https://check-dev.percona.com/v1/telemetry/GenericReport"]
    ]

telem_root_dir = '/usr/local/percona/telemetry/'

telem_history_dir=telem_root_dir + 'history'

def get_telemetry_command(timeout, interval, extra_options=""):
    telem_cmd="timeout --preserve-status "+ timeout + " ~/telemetry-agent/bin/telemetry-agent --telemetry.check-interval="+ interval + extra_options + " > " + telemetry_log_file
    return telem_cmd

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

@pytest.fixture()
def run_telemetry(host):
    host.run("timeout 2 ~/telemetry-agent/bin/telemetry-agent > ~/telemetry.log")

@pytest.fixture(scope="module")
def copy_pillar_metrics(host):
    with host.sudo("root"):
        if host.file(telem_root_dir).is_directory:
            print(f"{telem_root_dir} exists. Continue")
        else:
            print(f"Creating {telem_root_dir}. Continue")
            host.check_output(f"mkdir -p {telem_root_dir}")
        for pillar in pillars_list:
            pillar_dir=telem_root_dir + pillar
            if host.file(pillar_dir).is_directory:
                print(f"{pillar_dir} exists. Continue")
            else:
                print(f"Creating {pillar_dir}. Continue")
                host.check_output(f"mkdir -p {pillar_dir}")
            print(host.file(pillar_dir).listdir())
            if len(host.file(pillar_dir).listdir()) != 0:
                print("Clean up folder to have predictable num of files")
                for filename in host.file(pillar_dir).listdir():
                    print(f"{pillar_dir} + '/' + {filename}")
                    host.check_output(f"rm -rf {pillar_dir} + '/' + {filename}")
            print(f"{pillar_dir} does not have all files. Copiying pillar telemetry files")
            host.check_output(f"cp -p ./{pillar}-test-file.json {pillar_dir}/$(date +%s)-{pillar}-test-file.json")

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


def test_history_no_rights(host, copy_pillar_metrics):
    with host.sudo("root"):
        if host.file(telem_history_dir).is_directory:
            print(telem_history_dir + " exists")
            host.run(f"rm -rf {telem_history_dir}")
        host.check_output(f"chattr +i {telem_root_dir}")
    telem_cmd=get_telemetry_command("2", "10")
    check_result = host.run(telem_cmd)
    with host.sudo("root"):
        host.check_output(f"chattr -i {telem_root_dir}")
    assert check_result.rc != 0, (check_result.rc, check_result.stderr, check_result.stdout)


def test_telemetry_sending(host, copy_pillar_metrics):
    telem_cmd=get_telemetry_command("10", "5")
    host.check_output(telem_cmd)
    log_file_content = host.file(telemetry_log_file).content_string
    assert "sleeping for 5 seconds before first iteration" in log_file_content
    for pillar in pillars_list:
        assert 'Sending request to host=check-dev.percona.com.","file":"/usr/local/percona/telemetry/' + pillar in log_file_content
        assert 'Received response: 200 OK","file":"/usr/local/percona/telemetry/' + pillar in log_file_content

def test_telemetry_history(host,):
    log_file_content = host.file(telemetry_log_file).content_string
    for pillar in pillars_list:
        assert 'writing metrics to history file","pillar file":"/usr/local/percona/telemetry/' + pillar in log_file_content
        assert len(host.file(telem_history_dir).listdir()) == 3


# def test_telemetry_not_sent_wrong hist_permissions(host, copy_pillar_metrics):
#     host.run("timeout 25 ~/telemetry-agent/bin/telemetry-agent --telemetry.check-interval=10 > ~/telemetry.log")
#     cmd="cat ~/telemetry.log"

# def test_host_uuid_telemetry(host):
# def test_pg_telemetry(host):

# def test_mongo_telemetry(host):

# def test_telemetry_rerun(host):

# def test_no_files(host)

# def test_metrics(host)?
    
# def test_metrics_valid_json(host)?
    
# def test_resend_for_failure(host)?
    
# def test_files_cleaned_up(host)?

# def test_scrape_is_postponed(host):

# def test_history_created(host):
#     cmd="echo $PERCONA_TELEMETRY_URL"
#     output=host.run(cmd)
#     print(output)

# def test_env_var(host):
#     cmd="echo $PERCONA_TELEMETRY_URL"
#     output=host.run(cmd)
#     print(output)

# def run_agent(host):
#     cmd=" timeout 20 ./telemetry-agent --log.verbose --log.dev-mode --telemetry.check-interval=10"

# def test_history_cleanup

# def test_agent_defaults(host):
#     cmd="TEL_URL_VAR timeout 20 ./telemetry-agent --log.verbose --log.dev-mode --telemetry.check-interval=10"
#     host


################# WORKING SERVER
# def mysql_server(features=[]):
#     mysql_server = mysql.MySQL(base_dir, features)
#     mysql_server.start()
#     time.sleep(10)
#     return mysql_server


# def test_fips_md5():
#     server=mysql_server()
#     query="SELECT @@VERSION_COMMENT"
#     output = server.run_query(query)
#     server.stop()
#     print(output)
#     assert '00000000000000000000000000000000' in output
################# WORKING SERVER

# def test_fips_value(host,mysql_server):
#     if pro and fips_supported:
#         query="select @@ssl_fips_mode;"
#         output = mysql_server.run_query(query)
#         assert 'ON' in output
#     else:
#         pytest.skip("This test is only for PRO tarballs. Skipping")

# def test_fips_in_log(host, mysql_server):
#     if pro and fips_supported:
#         with host.sudo():
#             query="SELECT @@log_error;"
#             error_log = mysql_server.run_query(query)
#             logs=host.check_output(f'head -n30 {error_log}')
#             assert "A FIPS-approved version of the OpenSSL cryptographic library has been detected in the operating system with a properly configured FIPS module available for loading. Percona Server for MySQL will load this module and run in FIPS mode." in logs
#     else:
#         pytest.skip("This test is only for PRO tarballs. Skipping")

# def test_rocksdb_install(host, mysql_server):
#     host.run(mysql_server.psadmin+' --user=root -S'+mysql_server.socket+' --enable-rocksdb')
#     assert mysql_server.check_engine_active('ROCKSDB')


# def test_install_functions(mysql_server):
#     for function in ps_functions:
#         mysql_server.install_function(function[0], function[1], function[2])

# def test_install_component(mysql_server):
#     if ps_version_major == '8.0' or re.match(r'^8\.[1-9]$', ps_version_major):
#         for component in ps_components:
#             mysql_server.install_component(component)
#     else:
#         pytest.skip('Component is checked from 8.0!')

# def test_install_plugin(mysql_server):
#     for plugin in ps_plugins:
#         mysql_server.install_plugin(plugin[0], plugin[1])

# def test_audit_log_v2(mysql_server):
#     if ps_version_major in ['8.0']:
#         query='source {}/share/audit_log_filter_linux_install.sql;'.format(base_dir)
#         mysql_server.run_query(query)
#         query = 'SELECT plugin_status FROM information_schema.plugins WHERE plugin_name = "audit_log_filter";'
#         output = mysql_server.run_query(query)
#         assert 'ACTIVE' in output
#     else:
#         pytest.skip('audit_log_v2 is checked from 8.0!')
