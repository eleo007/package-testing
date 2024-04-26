#!/usr/bin/env python3
import pytest
import subprocess
import testinfra
import time
import os
import json
import shutil
import re
from packaging import version

RHEL_DISTS = ["redhat", "centos", "rhel", "oracleserver", "ol", "amzn"]

DEB_DISTS = ["debian", "ubuntu"]

os.environ['PERCONA_TELEMETRY_URL'] = 'https://check-dev.percona.com/v1/telemetry/GenericReport'
# os.environ['PERCONA_TELEMETRY_CHECK_INTERVAL'] = '10'
# TEL_URL_VAR="PERCONA_TELEMETRY_URL=https://check-dev.percona.com/v1/telemetry/GenericReport"

deployment = 'PACKAGE'

telemetry_log_file="/var/log/percona/telemetry-agent.log"

pillars_list=["ps", "pg", "psmdb"]

telem_root_dir = '/usr/local/percona/telemetry/'

telem_history_dir=telem_root_dir + 'history/'

dev_telem_url='https://check-dev.percona.com/v1/telemetry/GenericReport'

ta_service_name='percona-telemetry-agent'

# For tests when there is no package: create telemetry pillar directory if it is not present
def create_pillars_dir(host):
    with host.sudo("root"):
        pillar_users = {'pg':'postgres','ps':'mysql','pxc':'mysql','psmdb':'mongod'}
        for pillar in pillars_list:
            host.check_output(f"useradd {pillar_users[pillar]}")
            print(f"checking {pillar}")
            pillar_dir=telem_root_dir + pillar
            if host.file(pillar_dir).is_directory:
                print(f"{pillar_dir} exists. Continue")
            else:
                print(f"Creating {pillar_dir}.")
                host.check_output(f"mkdir -p {pillar_dir}")
                host.check_output(f"chown {pillar_users[pillar]}:percona-telemetry {pillar_dir}")
                host.check_output(f"chmod 775 {pillar_dir}")
                host.check_output(f"chmod g+s {pillar_dir}")
                host.check_output(f"chmod u+s {pillar_dir}")


# For tests when there is no pillar: create metrics files from templates.
# Crean up pillars directory to have predictable number of files for pillar we will add 1 file per pillar.
def clenup_pillar_dirs(host):
    with host.sudo("root"):
        for pillar in pillars_list:
            pillar_dir=telem_root_dir + pillar
            if len(host.file(pillar_dir).listdir()) != 0:
                print("Clean up folder to have predictable num of files")
                for metrics_filename in host.file(pillar_dir).listdir():
                    print(f"Removing metrics file {pillar_dir}/{metrics_filename}")
                    host.check_output(f"rm -rf {pillar_dir}/{metrics_filename}")

# For tests when there is no pillar: create metrics files from templates.
# To have predictable number of files for pillar we will add 1 file per pillar.
def create_pillar_metrics_file(host):
    metrics_files={}
    with host.sudo("root"):
        for pillar in pillars_list:
            pillar_dir=telem_root_dir + pillar
            print(f"{pillar_dir} does not have all files. Copiying pillar telemetry files")
            host.check_output(f"cp -p ./{pillar}-test-file.json {pillar_dir}/$(date +%s)-{pillar}-test-file.json")
            metrics_files[pillar]=' '.join(host.file(pillar_dir).listdir())
        return metrics_files

@pytest.fixture(scope="module")
def copy_pillar_metrics(host):
    create_pillars_dir(host)
    clenup_pillar_dirs(host)
    metrics_files = create_pillar_metrics_file(host)
    yield metrics_files

def set_ta_defaults(host, check_interval="", hist_keep_interval="", resend_timeout="", url=""):
    dist = host.system_info.distribution
    if dist.lower() in DEB_DISTS:
        options_file = '/etc/default/percona-telemetry-agent'
    else:
        options_file = '/etc/sysconfig/percona-telemetry-agent'
    if check_interval:
        host.check_output(f"sed -iE 's/PERCONA_TELEMETRY_CHECK_INTERVAL=.*$$/PERCONA_TELEMETRY_CHECK_INTERVAL={check_interval}/' {options_file}")
    if hist_keep_interval:
        host.check_output(f"sed -iE 's/PERCONA_TELEMETRY_HISTORY_KEEP_INTERVAL=.*$/PERCONA_TELEMETRY_HISTORY_KEEP_INTERVAL={hist_keep_interval}/' {options_file}")
    if resend_timeout:
        host.check_output(f"sed -iE 's/PERCONA_TELEMETRY_RESEND_INTERVAL=.*$/PERCONA_TELEMETRY_RESEND_INTERVAL={resend_timeout}/' {options_file}")
    if url:
        host.check_output(f"sed -iE 's/PERCONA_TELEMETRY_URL=.*$/PERCONA_TELEMETRY_URL={url}/' {options_file}")

def update_ta_options(host, check_interval="", hist_keep_interval="", resend_timeout="", url=""):
    set_ta_defaults(host, check_interval, hist_keep_interval, resend_timeout, url)
    cmd = 'systmctl restart' + ta_service_name
    host.check_output(cmd)
    time.sleep(int(check_interval)+2)

##################################################################################
#################################### TESTS #######################################
##################################################################################


# After pillar dirs are created and metrics are copied in copy_pillar_metrics, try to send telemetry
# TA log should contain info that telemetry was sent and receive code was 200
def test_telemetry_sending(host, copy_pillar_metrics):
    update_ta_options(host,'5', url=dev_telem_url)
    log_file_content = host.file(telemetry_log_file).content_string
    assert "sleeping for 5 seconds before first iteration" in log_file_content
    for pillar in pillars_list:
        assert 'Sending request to host=check-dev.percona.com.","file":"' + telem_root_dir + pillar + '/' + copy_pillar_metrics[pillar] in log_file_content
        assert 'Received response: 200 OK","file":"' + telem_root_dir + pillar + '/' + copy_pillar_metrics[pillar] in log_file_content

# After pillar dirs are created and metrics are copied in copy_pillar_metrics,
# TA log should contain info that history was written. History dir should contain 3 files (equal to num of sent telem files).
def test_telemetry_history_saved(host,copy_pillar_metrics):
    log_file_content = host.file(telemetry_log_file).content_string
    for pillar in pillars_list:
        assert 'writing metrics to history file","pillar file":"' + telem_root_dir + pillar + '/' + copy_pillar_metrics[pillar] in log_file_content
        assert 'failed to write history file","file":"' + telem_history_dir + copy_pillar_metrics[pillar] not in log_file_content
        assert len(host.file(telem_history_dir).listdir()) == 3

def test_tetemetry_removed_from_pillar(host,copy_pillar_metrics):
    log_file_content = host.file(telemetry_log_file).content_string
    for pillar in pillars_list:
        assert 'removing metrics file","file":"' + telem_root_dir + pillar + '/' + copy_pillar_metrics[pillar] in log_file_content
        assert 'failed to remove metrics file, will try on next iteration","file":"' + telem_root_dir + pillar + '/' + copy_pillar_metrics[pillar] not in log_file_content
        assert len (host.file(telem_root_dir + pillar).listdir()) == 0

def test_no_other_errors(host):
    log_file_content = host.file(telemetry_log_file).content_string
    assert '"level":"error"' not in log_file_content

def test_telemetry_file_valid_json(host, copy_pillar_metrics):
    for pillar in pillars_list:
        history_file=host.file(telem_history_dir + copy_pillar_metrics[pillar]).content_string
        json.loads(history_file)

def test_major_metrics_sent(host, copy_pillar_metrics):
    for pillar in pillars_list:
        history_file=host.file(telem_history_dir + copy_pillar_metrics[pillar]).content_string
        assert '"id":' in history_file
        assert '"createTime":' in history_file
        assert '"instanceId":' in history_file
        assert '"productFamily":' in history_file
        assert '"metrics":' in history_file
        assert '"installed_packages"' in history_file
        assert '"OS"' in history_file
        assert '"deployment"' in history_file
        assert '"hardware_arch"' in history_file

def test_major_metrics_values_sent(host, copy_pillar_metrics):
    # get OS
    test_host_version = host.system_info.distribution
    test_host_release = host.system_info.release
    test_host_arch = host.system_info.arch
    # get  instanceId
    telemetry_uuid_content = host.file('/usr/local/percona/telemetry_uuid').content_string
    pattern = r'instanceId: ([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})'
    match = re.search(pattern, telemetry_uuid_content)
    extracted_uuid = match.group(1)
    for pillar in pillars_list:
        history_file=host.file(telem_history_dir + copy_pillar_metrics[pillar]).content_string
        # get product family
        if pillar != 'pg':
            product_family = 'PRODUCT_FAMILY_' + pillar.upper()
        elif pillar == 'pg':
            product_family = 'PRODUCT_FAMILY_POSTGRESQL'
        else:
            assert 'Unknown pillar'

        history_dict=json.loads(history_file)
        assert re.search(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',history_dict['reports'][0]['id'])
        assert history_dict['reports'][0]['instanceId'] == extracted_uuid
        assert history_dict['reports'][0]['productFamily'] == product_family
        metrics_list=history_dict['reports'][0]['metrics']
        for metric in metrics_list:
            if metric['key'] == 'OS':
                assert test_host_version in metric['value'].lower()
                assert test_host_release in metric['value'].lower()
            if metric['key'] == 'deployment':
                assert deployment in metric['value']
            if metric['key'] == 'hardware_arch':
                assert test_host_arch in metric['value']

# On the first start of TA it should create history dir. If it can not for some reason (eg no rights) - TA terminates
# We remove TA history dir if present, make dir immutable and try to start TA. TA should terminate.
# def test_history_no_rights(host, copy_pillar_metrics):
#     with host.sudo("root"):
#         if host.file(telem_history_dir).is_directory:
#             print(telem_history_dir + " exists")
#             host.run(f"rm -rf {telem_history_dir}")
#         host.check_output(f"chattr +i {telem_root_dir}")
#     telem_cmd=get_ta_command("5", "10")
#     check_result = host.run(telem_cmd)
#     with host.sudo("root"):
#         host.check_output(f"chattr -i {telem_root_dir}")
#     assert check_result.rc != 0, (check_result.rc, check_result.stderr, check_result.stdout)

# check installed packages         assert '"installed_packages"' in history_file

# def test_test_OS_metrics():


# def test_telemetry_removed_from_history(host):
#     telem_cmd=get_ta_command("10", "5", "6")
#     host.check_output(telem_cmd)
#     log_file_content = host.file(telemetry_log_file).content_string
#     assert 'cleaning up history metric files","directory":"' + telem_history_dir in log_file_content
#     assert len(host.file(telem_history_dir).listdir()) == 0

# def test_no_perm_errors_with_packages()


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
