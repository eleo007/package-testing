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
import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')

PAK_VERSION = '0.1-1'
VERSION = os.getenv("VERSION")
REVISION = os.getenv("REVISION")

RHEL_DISTS = ["redhat", "centos", "rhel", "oracleserver", "ol", "amzn"]

DEB_DISTS = ["debian", "ubuntu"]

packages_list=['percona-server-mongodb','percona-backup-mongodb', 'percona-server-mongodb-mongos']

os.environ['PERCONA_TELEMETRY_URL'] = 'https://check-dev.percona.com/v1/telemetry/GenericReport'
# os.environ['PERCONA_TELEMETRY_CHECK_INTERVAL'] = '10'
# TEL_URL_VAR="PERCONA_TELEMETRY_URL=https://check-dev.percona.com/v1/telemetry/GenericReport"

telemetry_log_file="/var/log/percona/telemetry-agent.log"

pillars_list=["ps", "pg", "psmdb"]

telem_root_dir = '/usr/local/percona/telemetry/'

telem_history_dir=telem_root_dir + 'history/'

dev_telem_url='https:\\/\\/check-dev.percona.com\\/v1\\/telemetry\\/GenericReport'

ta_service_name='percona-telemetry-agent'

ps_pillar_dir = telem_root_dir + 'psmdb'

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
    with host.sudo("root"):
        cmd = 'systemctl stop ' + ta_service_name
        host.check_output(cmd)
        #clen up log file
        host.check_output(f'truncate -s 0 {telemetry_log_file}')
        set_ta_defaults(host, check_interval, hist_keep_interval, resend_timeout, url)
        cmd = 'systemctl restart ' + ta_service_name
        host.check_output(cmd)
    time.sleep(1)

def generate_pillar_record(host, file_num):
    with host.sudo("root"):
        for num in file_num:
            host.host.check_output('echo "\\{\\"check_mongo_packages_' + num + '\\":\\"\\check_mongo_packages_value"\\}"'\
                                   + ps_pillar_dir + '$(date +%s)-check_mongo_packages_' + num + '.json')
        time.sleep(1)

def test_mongo_pkg_scraped(host):
    update_ta_options(host, check_interval='10', url=dev_telem_url)
    generate_pillar_record(host, 1)
    time.sleep(10)
    log_file_content = host.file(telemetry_log_file).content_string
    assert 'scraping installed Percona packages' in log_file_content

@pytest.mark.parametrize("pkg_name", packages_list)
def test_ps_mandatory_packages(host, pkg_name):
    with host.sudo("root"):
        pillar_file_name = host.file('telem_history_dir').listdir()[0]
        hist_file = host.file(telem_history_dir + pillar_file_name).content_string
        hist_values=json.loads(hist_file)
        hist_metrics_list=hist_values['reports'][0]['metrics']
        for metric in hist_metrics_list:
            if metric['key'] == 'installed_packages':
                hist_packages_dict_str = metric['value']
                assert pkg_name.lower() in hist_packages_dict_str.lower()

def test_mongo_packages_values(host):
    with host.sudo("root"):
        pillar_file_name = host.file('telem_history_dir').listdir()[0]
        hist_file = host.file(telem_history_dir + pillar_file_name).content_string
        hist_values=json.loads(hist_file)
        hist_metrics_list=hist_values['reports'][0]['metrics']
        for metric in hist_metrics_list:
            if metric['key'] == 'installed_packages':
                hist_packages_dict_str = metric['value']
                hist_packages_dict = json.loads(hist_packages_dict_str)
                for ind in range(len(hist_packages_dict)):
                    hist_pkg_name = hist_packages_dict[ind]['name']
                    hist_pkg_version = hist_packages_dict[ind]['version']
                    hist_pkg_repo = hist_packages_dict[ind]['repository']
                    dist = host.system_info.distribution
                    # FOR DEB PACKAGES
                    if dist.lower() in DEB_DISTS:
                        # Get values of the packages installed on the server
                        # version of package
                        pkg_version_repo = host.run(f'apt-cache -q=0 policy {hist_pkg_name} | grep "\\*\\*\\*"')
                        pkg_version_match = re.search(r'[0-9]+\.[0-9]+(\.[0-9]+)?(-[0-9]+)?((-|.)[0-9]+)?',pkg_version_repo.stdout)
                        pkg_version = pkg_version_match.group(0)
                        if re.search(r'[0-9]+\.[0-9]+\.[0-9]+\-[0-9]+\.[0-9]+', pkg_version):
                            pkg_version = re.sub(r'.([0-9]+)$',r'-\g<1>', pkg_version)
                        # repository name and type
                        repo_url = host.run(f'apt-cache -q=0 policy {hist_pkg_name} | grep -A1 "\\*\\*\\*"| grep "http"')
                        repo_url_split = repo_url.stdout.strip(" ").split(" ")
                        url_repo_name = repo_url_split[1].split("/")[3]
                        url_repo_type = repo_url_split[2].split("/")[1]
                        if 'repo.percona' in repo_url.stdout and url_repo_type == 'main':
                            url_repo_type = 'release'
                        repository_str = "{'name': '" + url_repo_name + "', 'component': '"+ url_repo_type + "'}"
                    else:
                    # FOR RRPM PACKAGES
                        get_pkg_info = host.run(f"yum repoquery --qf '%{{version}}|%{{release}}|%{{from_repo}}' --installed {hist_pkg_name}")
                        pkg_info = get_pkg_info.stdout.strip('\n').split('|')
                        pkg_version, pkg_release, pkg_repository = pkg_info
                        pkg_release = pkg_release.replace('.','-')
                        pkg_full_version = pkg_version + '-' + pkg_release
                        pkg_version_match = re.search(r'[0-9]+\.[0-9]+(\.[0-9]+)?(-[0-9]+)?((-|.)[0-9]+)?', pkg_full_version)
                        pkg_version = pkg_version_match.group(0)
                        # print(pkg_version)
                        # get repository info. Values are empty if package was installed from commandline
                        if pkg_repository == '@commandline':
                            repository_str = "{'name': '', 'component': ''}"
                        else:
                            repo_name_full = pkg_repository.rstrip('-x86_64')
                            repo_name = '-'.join(repo_name_full.split('-')[0:-1])
                            repo_type = repo_name_full.split('-')[-1]
                            # print(repo_type)
                            # print(repo_name)
                            repository_str = "{'name': '" + repo_name + "', 'component': '"+ repo_type + "'}"
                            # print(pkg_version, pkg_release, pkg_repository, repo_name)
                    # Assert if values in history file differ from installed on server
                    assert re.search(r'[0-9]+\.[0-9]+\.[0-9]+\-[0-9]', pkg_version), hist_pkg_name
                    assert pkg_version == hist_pkg_version, hist_pkg_name
                    assert str(hist_pkg_repo) == repository_str, hist_pkg_name
                    # assert str(package['repository']) == repository_str