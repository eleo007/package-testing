#!/usr/bin/env python3
import pytest
import subprocess
import testinfra
import time
import os
import json
import shutil
import re
from datetime import datetime
from packaging import version

PAK_VERSION = '0.1-1'
VERSION = 'phase-0.1'
REVISION = '8502e528'

RHEL_DISTS = ["redhat", "centos", "rhel", "oracleserver", "ol", "amzn"]

DEB_DISTS = ["debian", "ubuntu"]

packages_list=['percona-toolkit','percona-Server-Server', 'percona-xtrabackup', 'percona-toolkit', 'percona-orchestrator', 'percona-haproxy', \
               'proxysql2', 'percona-mysql-shell', 'percona-mysql-router', 'pmm2-client']

os.environ['PERCONA_TELEMETRY_URL'] = 'https://check-dev.percona.com/v1/telemetry/GenericReport'
# os.environ['PERCONA_TELEMETRY_CHECK_INTERVAL'] = '10'
# TEL_URL_VAR="PERCONA_TELEMETRY_URL=https://check-dev.percona.com/v1/telemetry/GenericReport"

telemetry_log_file="/var/log/percona/telemetry-agent.log"

pillars_list=["ps", "pg", "psmdb"]

telem_root_dir = '/usr/local/percona/telemetry/'

telem_history_dir=telem_root_dir + 'history/'

dev_telem_url='https:\\/\\/check-dev.percona.com\\/v1\\/telemetry\\/GenericReport'

ta_service_name='percona-telemetry-agent'

telemetry_defaults=[["RootPath", "/usr/local/percona/telemetry"],["PSMetricsPath", "/usr/local/percona/telemetry/ps"],
         ["PSMDBMetricsPath", "/usr/local/percona/telemetry/psmdb"],["PXCMetricsPath", "/usr/local/percona/telemetry/pxc"],
        ["PGMetricsPath", "/usr/local/percona/telemetry/pg"], ["HistoryPath", "/usr/local/percona/telemetry/history"],
        ["CheckInterval", 86400], ["HistoryKeepInterval", 604800]
    ]

platform_defaults=[["ResendTimeout", 60], ["URL","https://check.percona.com/v1/telemetry/GenericReport"]
    ]

ps_telemetry_defaults=[["percona_telemetry.grace_interval", "86400"], ["percona_telemetry.history_keep_interval", "604800"],
                       ["percona_telemetry.scrape_interval", "86400"], ["percona_telemetry.telemetry_root_dir", "/usr/local/percona/telemetry/ps"],
                       ["percona_telemetry_disable","OFF"]
                    ]

ps_pillar_dir = telem_root_dir + 'ps'

def set_ta_defaults(host, check_interval="", hist_keep_interval="", resend_timeout="", url=""):
    dist = host.system_info.distribution
    if dist.lower() in DEB_DISTS:
        options_file = '/etc/default/percona-telemetry-agent'
    else:
        options_file = '/etc/sysconfig/percona-telemetry-agent'
    with host.sudo("root"):
        if check_interval:
            host.check_output(f"sed -iE 's/PERCONA_TELEMETRY_CHECK_INTERVAL=.*$/PERCONA_TELEMETRY_CHECK_INTERVAL={check_interval}/' {options_file}")
        if hist_keep_interval:
            host.check_output(f"sed -iE 's/PERCONA_TELEMETRY_HISTORY_KEEP_INTERVAL=.*$/PERCONA_TELEMETRY_HISTORY_KEEP_INTERVAL={hist_keep_interval}/' {options_file}")
        if resend_timeout:
            host.check_output(f"sed -iE 's/PERCONA_TELEMETRY_RESEND_INTERVAL=.*$/PERCONA_TELEMETRY_RESEND_INTERVAL={resend_timeout}/' {options_file}")
        if url:
            host.check_output(f"sed -iE 's/PERCONA_TELEMETRY_URL=.*$/PERCONA_TELEMETRY_URL={url}/' {options_file}")

def update_ta_options(host, check_interval="", hist_keep_interval="", resend_timeout="", url=""):
    set_ta_defaults(host, check_interval, hist_keep_interval, resend_timeout, url)
    cmd = 'systemctl restart ' + ta_service_name
    host.check_output(cmd)

def update_ps_options(host, grace_interval="", scrape_interval="", history_keep_interval=""):
    dist = host.system_info.distribution
    if dist.lower() in DEB_DISTS:
        mysql_cnf = '/etc/mysql/mysql.conf.d/mysqld.cnf'
    else:
        mysql_cnf = '/etc/my.cnf'
    with host.sudo("root"):
        if 'percona_telemetry_disable' in host.file(mysql_cnf).content_string:
            host.check_output(f"sed -r '/^percona_telemetry_disable=.*$/d' -i {mysql_cnf}")
        if grace_interval:
            host.check_output(f"sed -r '/^percona_telemetry.grace_interval=.*$/d' -i {mysql_cnf} && sed -r '$ a\\percona_telemetry.grace_interval={grace_interval}' -i {mysql_cnf}")
        if history_keep_interval:
            host.check_output(f"sed -r '/^percona_telemetry.history_keep_interval=.*$/d' -i {mysql_cnf} && sed -r '$ a\\percona_telemetry.history_keep_interval={history_keep_interval}' -i {mysql_cnf}")
        if scrape_interval:
            host.check_output(f"sed -r '/^percona_telemetry.scrape_interval=.*$/d' -i {mysql_cnf} && sed -r '$ a\\percona_telemetry.scrape_interval={scrape_interval}' -i {mysql_cnf}")
    cmd = 'systemctl restart mysql'
    host.check_output(cmd)
    time.sleep(5)

def generate_single_pillar_record(host):
    i = 0
    update_ps_options(host, "20","10")
    while i < 60:
        if len(host.file(ps_pillar_dir).listdir()) < 1:
            time.sleep(1)
            print('sleeping ' + str(i))
            i += 1
            if i == 59:
                pytest.fail(f'Telem file was not generated for 1 minute!')
        elif len(host.file(ps_pillar_dir).listdir()) == 1:
            with host.sudo("root"):
                host.run('systemctl stop mysql')
                telem_file_name=host.file(ps_pillar_dir).listdir()[0]
                host.run(f'mkdir -p /package-testing/telemetry/reference/')
                host.run(f'cp {ps_pillar_dir}/{telem_file_name} /package-testing/telemetry/reference/')
                return telem_file_name
        else:
            pytest.fail(f'More than 1 telemetry file was generated!')

#########################################
############# TA PACKAGE  ###############
#########################################


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
    assert "percona-telemetry-agent" in ta_serv.systemd_properties["EnvironmentFiles"]

def test_mysql_service(host):
    mysql_serv = host.service("mysql")
    assert mysql_serv.is_running

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

def test_ps_pillar_dirs(host):
    assert host.file(ps_pillar_dir).is_directory
    assert host.file(ps_pillar_dir).user == 'mysql'
    assert host.file(ps_pillar_dir).group == 'percona-telemetry'
    assert oct(host.file(ps_pillar_dir).mode) == '0o6775'

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

###############################################
################## MYSQL ######################
###############################################

#########################################
############# TA FUNCTIONS  #############
#########################################

def test_telemetry_scrape_postponed(host):
    host.run('systemctl stop mysql')
    host.run(f'rm -rf {ps_pillar_dir}/*')
    generate_single_pillar_record(host)
    update_ta_options(host, check_interval='10', url=dev_telem_url)
    time.sleep(7)
    ta_log_file_content = host.file(telemetry_log_file).content_string
    assert "sleeping for 10 seconds before first iteration" in ta_log_file_content
    assert "start metrics processing iteration" not in ta_log_file_content
    assert len(host.file(ps_pillar_dir).listdir()) == 1

def test_telemetry_sending(host):
    pillar_ref_file = host.file('/package-testing/telemetry/reference/').listdir()[0]
    i = 0
    time.sleep(20)
    log_file_content = host.file(telemetry_log_file).content_string
    assert 'Sending request to host=check-dev.percona.com.","file":"' + ps_pillar_dir + '/' + pillar_ref_file in log_file_content
    assert 'Received response: 200 OK","file":"' + ps_pillar_dir + '/' + pillar_ref_file in log_file_content

# def test_telemetry_uuid_created(host):
#     telem_uuid_file="/usr/local/percona/telemetry_uuid"
#     assert host.file(telem_uuid_file).is_file
#     pattern = r'instanceId:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})'
#     telemetry_uuid_content = host.file(telem_uuid_file).content_string
#     assert re.search(pattern, telemetry_uuid_content)

def test_telemetry_history_saved(host):
    pillar_ref_file = host.file('/package-testing/telemetry/reference/').listdir()[0]
    log_file_content = host.file(telemetry_log_file).content_string
    assert 'writing metrics to history file","pillar file":"' + ps_pillar_dir + '/' + pillar_ref_file in log_file_content
    assert 'failed to write history file","file":"' + telem_history_dir + pillar_ref_file not in log_file_content
    assert len(host.file(telem_history_dir).listdir()) == 1

def test_tetemetry_removed_from_pillar(host):
    pillar_ref_file = host.file('/package-testing/telemetry/reference/').listdir()[0]
    log_file_content = host.file(telemetry_log_file).content_string
    assert 'removing metrics file","file":"' + ps_pillar_dir + '/' + pillar_ref_file in log_file_content
    assert 'failed to remove metrics file, will try on next iteration","file":"' + ps_pillar_dir + '/' + pillar_ref_file not in log_file_content
    assert len(host.file(ps_pillar_dir).listdir()) == 0

def test_no_other_errors(host):
    log_file_content = host.file(telemetry_log_file).content_string
    assert '"level":"error"' not in log_file_content

def test_telemetry_history_file_valid_json(host):
    pillar_ref_file = host.file('/package-testing/telemetry/reference/').listdir()[0]
    history_file=host.file(telem_history_dir + pillar_ref_file).content_string
    assert json.loads(history_file)

def test_installed_packages_scraped(host):
    log_file_content = host.file(telemetry_log_file).content_string
    assert 'scraping installed Percona packages' in log_file_content

def test_ta_metrics_sent(host):
    pillar_ref_file = host.file('/package-testing/telemetry/reference/').listdir()[0]
    history_file = host.file(telem_history_dir + pillar_ref_file).content_string
    assert '"id":' in history_file
    assert '"createTime":' in history_file
    assert '"instanceId":' in history_file
    assert '"productFamily":' in history_file
    assert '"metrics":' in history_file
    assert '"installed_packages"' in history_file
    assert '"OS"' in history_file
    assert '"deployment"' in history_file
    assert '"hardware_arch"' in history_file

def test_ta_metrics_values_sent(host):
    # get OS
    test_host_os = host.run("grep PRETTY_NAME /etc/os-release | sed 's/PRETTY_NAME=//g;s/\"//g'").stdout
    test_host_arch = host.system_info.arch
    # get  instanceId from telemetry_uuid
    telemetry_uuid_content = host.file('/usr/local/percona/telemetry_uuid').content_string
    pattern = r'instanceId:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})'
    match = re.search(pattern, telemetry_uuid_content)
    extracted_uuid = match.group(1)

    # check metrics in the history files
    pillar_ref_file = host.file('/package-testing/telemetry/reference/').listdir()[0]
    history_file=host.file(telem_history_dir + pillar_ref_file).content_string

    history_dict=json.loads(history_file)
    assert re.search(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',history_dict['reports'][0]['id'])
    assert datetime.strptime(history_dict['reports'][0]['createTime'], "%Y-%m-%dT%H:%M:%SZ")
    assert history_dict['reports'][0]['instanceId'] == extracted_uuid
    assert history_dict['reports'][0]['productFamily'] == 'PRODUCT_FAMILY_PS'
    # check metrics
    metrics_list=history_dict['reports'][0]['metrics']
    for metric in metrics_list:
        if metric['key'] == 'OS':
            assert metric['value'] in test_host_os
        if metric['key'] == 'deployment':
            assert 'PACKAGE' in metric['value']
        if metric['key'] == 'hardware_arch':
            assert test_host_arch in metric['value']

def test_ps_metrics_sent(host):
    # check metrics in the history files
    pillar_ref_name = host.file('/package-testing/telemetry/reference/').listdir()[0]
    pillar_ref_file = host.file('/package-testing/telemetry/reference/' + pillar_ref_name).content_string
    reference_dict = json.loads(pillar_ref_file)
    ref_uptime = reference_dict['uptime']
    ref_databases_count = reference_dict['databases_count']
    ref_databases_size = reference_dict['databases_size']
    ref_se_engines_in_use = str(reference_dict['se_engines_in_use']).replace('\'', '\"').replace(' ', '')
    ref_db_instance_id = reference_dict['db_instance_id']
    ref_pillar_version = reference_dict['pillar_version']
    # ref_replication_info = reference_dict['replication_info']
    ref_active_plugins = str(reference_dict['active_plugins']).replace('\'', '\"').replace(' ', '')
    ref_active_components = str(reference_dict['active_components']).replace('\'', '\"').replace(' ', '')
    # get content of pillar history file
    history_file = host.file(telem_history_dir + pillar_ref_name).content_string
    with host.sudo("root"):
        host.run(f'mkdir -p /package-testing/telemetry/reference/hist')
        host.run(f"cp {telem_history_dir}{pillar_ref_name} /package-testing/telemetry/reference/hist/")
    history_dict = json.loads(history_file)
    # check metrics
    metrics_list=history_dict['reports'][0]['metrics']
    for metric in metrics_list:
        if metric['key'] == 'uptime':
            assert metric['value'] == ref_uptime
        if metric['key'] == 'databases_count':
            assert metric['value'] == ref_databases_count
        if metric['key'] == 'databases_size':
            assert metric['value'] == ref_databases_size
        if metric['key'] == 'se_engines_in_use':
            assert metric['value'] == ref_se_engines_in_use
        if metric['key'] == 'db_instance_id':
            assert metric['value'] == ref_db_instance_id
        if metric['key'] == 'pillar_version':
            assert metric['value'] == ref_pillar_version
        if metric['key'] == 'active_plugins':
            assert metric['value'] == ref_active_plugins
        if metric['key'] == 'active_components':
            assert metric['value'] == ref_active_components

@pytest.mark.parametrize("pack_name", packages_list)
def test_ps_mandatory_packages(host, pack_name):
    pillar_ref_name = host.file('/package-testing/telemetry/reference/').listdir()[0]
    hist_file = host.file(telem_history_dir + pillar_ref_name).content_string
    hist_values=json.loads(hist_file)
    hist_metrics_list=hist_values['reports'][0]['metrics']
    for metric in hist_metrics_list:
        if metric['key'] == 'installed_packages':
            hist_packages_dict_str = metric['value']
            assert pack_name.lower() in hist_packages_dict_str.lower()

def test_ps_packages_values(host):
    pillar_ref_name = host.file('/package-testing/telemetry/reference/').listdir()[0]
    hist_file = host.file(telem_history_dir + pillar_ref_name).content_string
    hist_values=json.loads(hist_file)
    hist_metrics_list=hist_values['reports'][0]['metrics']
    for metric in hist_metrics_list:
        if metric['key'] == 'installed_packages':
            hist_packages_dict_str = metric['value']
            hist_packages_dict = json.loads(hist_packages_dict_str)
            for ind in range(len(hist_packages_dict)):
                hist_pack_name = hist_packages_dict[ind]['name']
                hist_pack_version = hist_packages_dict[ind]['version']
                hist_pack_repo = hist_packages_dict[ind]['repository']
                dist = host.system_info.distribution
                # FOR DEB PACKAGES
                if dist.lower() in DEB_DISTS:
                    # Get values of the packages installed on the server
                    # version of package
                    pack_version_repo = host.run(f'apt-cache -q=0 policy {hist_pack_name} | grep "\\*\\*\\*"')
                    print(pack_version_repo.stdout)
                    pack_version_match = re.search(r'[0-9]+\.[0-9]+(\.[0-9]+)?(-[0-9]+)?((-|.)[0-9]+)?',pack_version_repo.stdout)
                    pack_version = pack_version_match.group(0)
                    # repository name and type
                    repo_url = host.run(f'apt-cache -q=0 policy {hist_pack_name} | grep -A1 "\\*\\*\\*"| grep "http"')
                    repo_url_split = repo_url.stdout.strip(" ").split(" ")
                    url_repo_name = repo_url_split[1].split("/")[3]
                    url_repo_type = repo_url_split[2].split("/")[1]
                    if 'repo.percona' in repo_url.stdout and url_repo_type == 'main':
                        url_repo_type = 'release'
                    repository_str = "{'name': '" + url_repo_name + "', 'component': '"+ url_repo_type + "'}"
                else:
                # FOR RRPM PACKAGES
                    get_pack_info = host.run(f"yum repoquery --qf '%{{version}}|%{{release}}|%{{from_repo}}' --installed {hist_pack_name}")
                    pack_info = get_pack_info.stdout.strip('\n').split('|')
                    pack_version, pack_release, pack_repository = pack_info
                    pack_release = pack_release.replace('.','-')
                    pack_full_version = pack_version + '-' + pack_release
                    pack_version_match = re.search(r'[0-9]+\.[0-9]+(\.[0-9]+)?(-[0-9]+)?((-|.)[0-9]+)?', pack_full_version)
                    pack_version = pack_version_match.group(0)
                    # print(pack_version)
                    # get repository info. Values are empty if package was installed from commandline
                    if pack_repository == '@commandline':
                        repository_str = "{'name': '', 'component': ''}"
                    else:
                        repo_name_full = pack_repository.rstrip('-x86_64')
                        repo_name = '-'.join(repo_name_full.split('-')[0:-1])
                        repo_type = repo_name_full.split('-')[-1]
                        # print(repo_type)
                        # print(repo_name)
                        repository_str = "{'name': '" + repo_name + "', 'component': '"+ repo_type + "'}"
                        # print(pack_version, pack_release, pack_repository, repo_name)
                # Assert if values in history file differ from installed on server
                assert pack_version == hist_pack_version, hist_pack_name
                assert str(hist_pack_repo) == repository_str, hist_pack_name
                # assert str(package['repository']) == repository_str