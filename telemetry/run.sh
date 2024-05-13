#!/usr/bin/env bash
export PATH=${HOME}/.local/bin:${PATH}

echo "Installing dependencies..."
if [ -f /etc/redhat-release ]; then
  sudo yum install -y libaio numactl openssl tar
  # below needed for 5.6 mysql_install_db
  sudo yum install -y perl-Data-Dumper
  if [ $(grep -c "release 6" /etc/redhat-release) -eq 1 ]; then
    sudo yum install -y epel-release centos-release-scl
    sudo yum install -y rh-python36 rh-python36-python-pip
    source /opt/rh/rh-python36/enable
  else
    sudo yum install -y python3 python3-pip
  fi
else
  UCF_FORCE_CONFOLD=1 DEBIAN_FRONTEND=noninteractive sudo -E apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qq -y install openssl
  if [[ $(lsb_release -sc) == 'xenial' ]]; then
    DEBIAN_FRONTEND=noninteractive sudo add-apt-repository -y ppa:deadsnakes/ppa 
    DEBIAN_FRONTEND=noninteractive sudo apt update
    DEBIAN_FRONTEND=noninteractive sudo apt -y install python3.6 
    sudo rm /usr/bin/python3 && sudo ln -sf /usr/bin/python3.6 /usr/bin/python3
    wget -O get-pip.py "https://bootstrap.pypa.io/get-pip.py" && sudo python3 get-pip.py
  else
    sudo apt install -y python3 python3-pip
  fi
  sudo apt-get update -y
  sudo apt install -y libaio1 libnuma1 libldap-2.4-2
fi

if [[ $(lsb_release -sc) == 'bookworm' ]]; then
  pip3 install --user --break-system-packages pytest-testinfra pytest
else
  pip3 install --user pytest-testinfra pytest
fi

if [ -z "${PS_VERSION}" ]; then
  echo "PS_VERSION environment variable needs to be set!"
  echo "export PS_VERSION=\"8.0.17-8\""
fi

if [ -z "${BASE_DIR}" ]; then
  echo "BASE_DIR environment variable needs to be set!"
  exit 1
fi

echo "Running tests..."
python3 -m pytest -v --junit-xml report.xml $@