#!/usr/bin/env python3
import os
import re

# base_dir = os.getenv('BASE_DIR')
# ps_version = os.getenv('PS_VERSION')
# ps_revision = os.getenv('PS_REVISION')

base_dir = "/home/eleonora/sandbox/Percona-Server-8.0.31-23-Linux.x86_64.glibc2.17-minimal"
ps_version = "8.0.31-23"
# ps_revision = os.getenv('PS_REVISION')

ps_version_upstream, ps_version_percona = ps_version.split('-')
ps_version_major = ps_version_upstream.split('.')[0] + '.' + ps_version_upstream.split('.')[1]

# 8.0
ps80_plugins = (
  ('audit_log','audit_log.so'),('mysql_no_login','mysql_no_login.so'),('validate_password','validate_password.so'),
  ('version_tokens','version_token.so'),('rpl_semi_sync_master','semisync_master.so'),('rpl_semi_sync_slave','semisync_slave.so'),
  ('group_replication','group_replication.so'),('clone','mysql_clone.so'),('data_masking','data_masking.so'),
  ('procfs', 'procfs.so'), ('authentication_ldap_sasl','authentication_ldap_sasl.so')
)
ps80_functions = (
  ('fnv1a_64', 'libfnv1a_udf.so', 'INTEGER'),('fnv_64', 'libfnv_udf.so', 'INTEGER'),('murmur_hash', 'libmurmur_udf.so', 'INTEGER'),
  ('version_tokens_set', 'version_token.so', 'STRING'),('version_tokens_show', 'version_token.so', 'STRING'),('version_tokens_edit', 'version_token.so', 'STRING'),
  ('version_tokens_delete', 'version_token.so', 'STRING'),('version_tokens_lock_shared', 'version_token.so', 'INT'),('version_tokens_lock_exclusive', 'version_token.so', 'INT'),
  ('version_tokens_unlock', 'version_token.so', 'INT'),('service_get_read_locks', 'locking_service.so', 'INT'),('service_get_write_locks', 'locking_service.so', 'INT'),
  ('service_release_locks', 'locking_service.so', 'INT'), ('get_binlog_by_gtid', 'binlog_utils_udf.so', 'STRING'), ('get_last_gtid_from_binlog', 'binlog_utils_udf.so', 'STRING'),
  ('get_gtid_set_by_binlog', 'binlog_utils_udf.so', 'STRING'), ('get_binlog_by_gtid_set', 'binlog_utils_udf.so', 'STRING'), ('get_first_record_timestamp_by_binlog', 'binlog_utils_udf.so', 'STRING'),
  ('get_last_record_timestamp_by_binlog', 'binlog_utils_udf.so', 'STRING')
)

ps80_components = (
  'component_masking_functions','component_validate_password', 'component_log_sink_syseventlog',
  'component_log_sink_json', 'component_log_filter_dragnet',
  'component_audit_api_message_emit'
)

#####

ps_plugins = ps80_plugins
ps_functions = ps80_functions
ps_components = ps80_components

