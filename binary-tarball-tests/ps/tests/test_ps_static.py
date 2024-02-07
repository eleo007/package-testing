#!/usr/bin/env python3
import pytest
import testinfra
import pathlib
import lddwrap

from settings import *

def test_executables_exist(host):
    for executable in ps_executables:
        assert host.file(base_dir+'/'+executable).exists
        assert oct(host.file(base_dir+'/'+executable).mode) == '0o755'

def test_binaries_version(host):
    if ps_version_major in ['5.7','5.6']:
        assert 'mysql  Ver 14.14 Distrib '+ps_version+', for Linux (x86_64)' in host.check_output(base_dir+'/bin/mysql --version')
        assert 'mysqld  Ver '+ps_version+' for Linux on x86_64 (Percona Server (GPL), Release '+ps_version_percona+', Revision '+ps_revision+')' in host.check_output(base_dir+'/bin/mysqld --version')
    else:
        assert 'mysql  Ver '+ ps_version +' for Linux on x86_64 (Percona Server Pro (GPL), Release '+ ps_version_percona +', Revision '+ ps_revision +')' in host.check_output(base_dir+'/bin/mysql --version')
        assert 'mysqld  Ver '+ ps_version +' for Linux on x86_64 (Percona Server Pro (GPL), Release '+ ps_version_percona +', Revision '+ ps_revision +')' in host.check_output(base_dir+'/bin/mysqld --version')

def test_files_exist(host):
    for f in ps_files:
        assert host.file(base_dir+'/'+f).exists
        assert host.file(base_dir+'/'+f).size != 0


def test_symlinks(host):
    for symlink in ps_symlinks:
        assert host.file(base_dir+'/'+symlink[0]).is_symlink
        assert host.file(base_dir+'/'+symlink[0]).linked_to == base_dir+'/'+symlink[1]
        assert host.file(base_dir+'/'+symlink[1]).exists

def test_openssl_symlinks_not_exist(host):
    for openssl_symlink in ps_openssl_symlinks:
        assert not host.file(base_dir+'/'+openssl_symlink).exists

def test_binaries_linked_libraries(host):
    for binary in ps_binaries:
        assert '=> not found' not in host.check_output('ldd ' + base_dir + '/' + binary)

ps80_openssl_symlinks = ('libcrypto.so', 'libk5crypto.so', 'libssl.so', 'libsasl2.so')

path = pathlib.Path('/home/vagrant/Percona-Server-Pro-8.0.35-27-Linux.x86_64.glibc2.35/bin/mysqld')
deps = lddwrap.list_dependencies(path=path)
for dep in deps:
#  print(dep.soname)
  if dep.soname is not None:
    for openssl_so in ps80_openssl_symlinks:
      if openssl_so in dep.soname:
        print(dep.path)
