FROM ubuntu:16.04

LABEL maintainer="dev@mirantis.com"

ENV DEBIAN_FRONTEND=noninteractive \
    DEBCONF_NONINTERACTIVE_SEEN=true \
    LANG=C.UTF-8 \
    LANGUAGE=$LANG \
    PYTEST_REPORT_DIR=/var/lib/validation_artifacts
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

USER root
ARG UBUNTU_MIRROR_URL="http://archive.ubuntu.com/ubuntu"
ARG SL_TEST_REPO='http://gerrit.mcp.mirantis.com/mcp/stacklight-pytest'
ARG SL_TEST_BRANCH='master'
ENV PYTHONHTTPSVERIFY=0

WORKDIR /var/lib/
COPY bin/ /usr/local/bin/
COPY test_set/ ./
#
RUN set -exo pipefail; pushd /etc/apt/ && echo > sources.list && \
    echo 'Acquire::Languages "none";' > apt.conf.d/docker-no-languages && \
    echo 'Acquire::GzipIndexes "true"; Acquire::CompressionTypes::Order:: "gz";' > apt.conf.d/docker-gzip-indexes && \
    echo 'APT::Get::Install-Recommends "false"; APT::Get::Install-Suggests "false";' > apt.conf.d/docker-recommends && \
    echo "deb [arch=amd64] $UBUNTU_MIRROR_URL xenial main restricted universe multiverse" >> sources.list && \
    echo "deb [arch=amd64] $UBUNTU_MIRROR_URL xenial-updates main restricted universe multiverse" >> sources.list && \
    echo "deb [arch=amd64] $UBUNTU_MIRROR_URL xenial-backports main restricted universe multiverse" >> sources.list && \
    popd ; apt-get update && apt-get  upgrade -y && \
    apt-get install -y build-essential curl git-core iputils-ping libffi-dev libldap2-dev libsasl2-dev libssl-dev patch python-dev python-pip python3-dev python3-pip  vim-tiny wget \
    python-virtualenv \
# Enable these packages while porting to Python3  =>  python3-virtualenv python3-dev  \
# Due to upstream bug we should use fixed version of pip
    && pip install -U pip==20.0.2  \
    && pip install tox  \
    # initialize cvp stacklight test suite
        && mkdir cvp-stacklight \
        && pushd cvp-stacklight  \
        && git clone -b $SL_TEST_BRANCH $SL_TEST_REPO  \
        && pushd stacklight-pytest \
        && git log -n1 \
        && popd && popd  \
        && tox --recreate \
# Cleanup
    && apt-get -y purge libx11-data xauth libxmuu1 libxcb1 libx11-6 libxext6 ppp pppconfig pppoeconf popularity-contest cpp gcc g++ libssl-doc && \
    apt-get -y autoremove; apt-get -y clean ; rm -rf /root/.cache; rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/* ; rm -rf /var/tmp/* ; rm -rfv /etc/apt/sources.list.d/* ; echo > /etc/apt/sources.list \

# Download iperf package
    && wget http://ftp.br.debian.org/debian/pool/main/i/iperf/iperf_2.0.5+dfsg1-2_amd64.deb -O /var/lib/iperf_2.0.5+dfsg1-2_amd64.deb

ENTRYPOINT ["entrypoint.sh"]
# docker build --no-cache -t cvp-sanity-checks:test_latest .
