import pytest
import json
import os
import logging


def test_k8s_get_cs_status(local_salt_client):
    result = local_salt_client.cmd(
        tgt='etcd:server',
        param='kubectl get cs',
        expr_form='pillar'
    )
    errors = []
    if not result:
        pytest.skip("k8s is not found on this environment")
    for node in result:
        for line in result[node].split('\n'):
            line = line.strip()
            if 'MESSAGE' in line or 'proto' in line:
                continue
            else:
                if 'Healthy' not in line:
                    errors.append(line)
        break
    assert not errors, 'k8s is not healthy:\n{}'.format(
        json.dumps(errors, indent=4))


@pytest.mark.xfail
def test_k8s_get_nodes_status(local_salt_client):
    result = local_salt_client.cmd(
        tgt='etcd:server',
        param='kubectl get nodes',
        expr_form='pillar'
    )
    errors = []
    if not result:
        pytest.skip("k8s is not found on this environment")
    for node in result:
        for line in result[node].split('\n'):
            line = line.strip()
            if 'STATUS' in line or 'proto' in line:
                continue
            else:
                if 'Ready' != line.split()[1]:
                    errors.append(line)
        break
    assert not errors, 'k8s is not healthy:\n{}'.format(
        json.dumps(errors, indent=4))


def test_k8s_get_calico_status(local_salt_client):
    result = local_salt_client.cmd(
        tgt='kubernetes:pool',
        param='calicoctl node status',
        expr_form='pillar'
    )
    errors = []
    if not result:
        pytest.skip("k8s is not found on this environment")
    for node in result:
        for line in result[node].split('\n'):
            line = line.strip('|')
            if 'STATE' in line or '| ' not in line:
                continue
            else:
                if 'up' not in line or 'Established' not in line:
                    errors.append(line)
    assert not errors, 'Calico node status is not good:\n{}'.format(
        json.dumps(errors, indent=4))


def test_k8s_cluster_status(local_salt_client):
    result = local_salt_client.cmd(
        tgt='kubernetes:master',
        param='kubectl cluster-info',
        expr_form='pillar'
    )
    errors = []
    if not result:
        pytest.skip("k8s is not found on this environment")
    for node in result:
        for line in result[node].split('\n'):
            if 'proto' in line or 'further' in line or line == '':
                continue
            else:
                if 'is running' not in line:
                    errors.append(line)
        break
    assert not errors, 'k8s cluster info is not good:\n{}'.format(
        json.dumps(errors, indent=4))


def test_k8s_kubelet_status(local_salt_client):
    result = local_salt_client.cmd(
        tgt='kubernetes:pool',
        fun='service.status',
        param='kubelet',
        expr_form='pillar'
    )
    errors = []
    if not result:
        pytest.skip("k8s is not found on this environment")
    for node in result:
        if not result[node]:
            errors.append(node)
    assert not errors, 'Kublete is not running on the nodes:\n{}'.format(
        errors)


def test_k8s_check_system_pods_status(local_salt_client):
    result = local_salt_client.cmd(
        tgt='etcd:server',
        param='kubectl --namespace="kube-system" get pods',
        expr_form='pillar'
    )
    errors = []
    if not result:
        pytest.skip("k8s is not found on this environment")
    for node in result:
        for line in result[node].split('\n'):
            line = line.strip('|')
            if 'STATUS' in line or 'proto' in line:
                continue
            else:
                if 'Running' not in line:
                    errors.append(line)
        break
    assert not errors, 'Some system pods are not running:\n{}'.format(
        json.dumps(errors, indent=4))


def test_check_k8s_image_availability(local_salt_client):
    # not a test actually
    hostname = 'https://docker-dev-virtual.docker.mirantis.net/artifactory/webapp/'
    response = os.system('curl -s --insecure {} > /dev/null'.format(hostname))
    if response == 0:
        logging.info('{} is AVAILABLE'.format(hostname))
    else:
        logging.error('{} IS NOT AVAILABLE'.format(hostname))


@pytest.mark.xfail
def test_k8s_dashboard_available(local_salt_client):
    """
        # Check is kubernetes enabled on the cluster with command  `salt -C 'etcd:server' cmd.run 'kubectl get svc -n kube-system'`
        # If yes then check Dashboard addon with next command: `salt -C 'etcd:server' pillar.get kubernetes:common:addons:dashboard:enabled`
        # If dashboard enabled get its IP from pillar `salt -C 'etcd:server' pillar.get kubernetes:common:addons:dashboard:public_ip`
        # Check that public_ip exists
        # Check that public_ip:8443 is accessible with curl
    """
    result = local_salt_client.cmd(
        tgt='etcd:server',
        param='kubectl get svc -n kube-system',
        expr_form='pillar'
    )
    if not result:
        pytest.skip("k8s is not found on this environment")

    # service name 'kubernetes-dashboard' is hardcoded in kubernetes formula
    dashboard_enabled = local_salt_client.pillar_get(
        tgt='etcd:server',
        param='kubernetes:common:addons:dashboard:enabled',)
    if not dashboard_enabled:
        pytest.skip("Kubernetes dashboard is not enabled in the cluster.")

    external_ip = local_salt_client.pillar_get(
        tgt='etcd:server',
        param='kubernetes:common:addons:dashboard:public_ip')

    assert external_ip, (
        "Kubernetes dashboard public ip is not found in pillars")
    assert external_ip.__len__() > 0, (
        "Kubernetes dashboard is enabled but not defined in pillars")
    # dashboard port 8443 is hardcoded in kubernetes formula
    url = "https://{}:8443".format(external_ip)
    check = local_salt_client.cmd(
        tgt='etcd:server',
        param='curl {} 2>&1 | grep kubernetesDashboard'.format(url),
        expr_form='pillar'
    )
    assert len(list(check.values())[0]) != 0, (
        'Kubernetes dashboard is not reachable on {} from '
        'ctl nodes'.format(url)
    )
