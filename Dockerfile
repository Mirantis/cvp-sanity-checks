FROM ubuntu:16.04

LABEL maintainer="dev@mirantis.com"

ENV DEBIAN_FRONTEND=noninteractive \
    DEBCONF_NONINTERACTIVE_SEEN=true \
    LANG=C.UTF-8 \
    LANGUAGE=$LANG
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

USER root
ARG UBUNTU_MIRROR_URL="http://archive.ubuntu.com/ubuntu"

WORKDIR /var/lib/
COPY bin/ /usr/local/bin/
COPY test_set/ ./
#
RUN set -ex; pushd /etc/apt/ && echo > sources.list && \
    echo 'Acquire::Languages "none";' > apt.conf.d/docker-no-languages && \
    echo 'Acquire::GzipIndexes "true"; Acquire::CompressionTypes::Order:: "gz";' > apt.conf.d/docker-gzip-indexes && \
    echo 'APT::Get::Install-Recommends "false"; APT::Get::Install-Suggests "false";' > apt.conf.d/docker-recommends && \
    echo "deb [arch=amd64] $UBUNTU_MIRROR_URL xenial main restricted universe multiverse" >> sources.list && \
    echo "deb [arch=amd64] $UBUNTU_MIRROR_URL xenial-updates main restricted universe multiverse" >> sources.list && \
    echo "deb [arch=amd64] $UBUNTU_MIRROR_URL xenial-backports main restricted universe multiverse" >> sources.list && \
    popd ; apt-get update && apt-get  upgrade -y && \
    apt-get install -y build-essential curl git-core iputils-ping libffi-dev libldap2-dev libsasl2-dev libssl-dev patch python-dev python-pip python3-dev vim-tiny wget \
    python-virtualenv python3-virtualenv && \
# Due to upstream bug we should use fixed version of pip
    python -m pip install --upgrade 'pip==9.0.3' \
    # initialize cvp sanity test suite
          && pushd cvp_sanity  \
          && virtualenv  venv \
          && . venv/bin/activate \
          && pip install -r requirements.txt \
          && deactivate \
          && popd \
    # initialize cvp spt test suite
          && pushd cvp_spt  \
          && virtualenv  venv \
          && . venv/bin/activate \
          && pip install -r requirements.txt \
          && deactivate \
          && popd && \
# Cleanup
    apt-get -y purge libx11-data xauth libxmuu1 libxcb1 libx11-6 libxext6 ppp pppconfig pppoeconf popularity-contest cpp gcc g++ libssl-doc && \
    apt-get -y autoremove; apt-get -y clean ; rm -rf /root/.cache; rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/* ; rm -rf /var/tmp/* ; rm -rfv /etc/apt/sources.list.d/* ; echo > /etc/apt/sources.list

ENTRYPOINT ["entrypoint.sh"]
# docker build --no-cache -t cvp-sanity-checks:test_latest .
