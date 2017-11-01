import pytest
import json
import os


def test_k8s_get_cs_status(local_salt_client):
    result = local_salt_client.cmd(
        'etcd:server', 'cmd.run',
        ['kubectl get cs'],
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
    assert not errors, 'k8s is not healthy: {}'.format(json.dumps(
                                                       errors,
                                                       indent=4))


def test_k8s_get_nodes_status(local_salt_client):
    result = local_salt_client.cmd(
        'etcd:server', 'cmd.run',
        ['kubectl get nodes'],
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
                if 'Ready' not in line:
                    errors.append(line)
        break
    assert not errors, 'k8s is not healthy: {}'.format(json.dumps(
                                                       errors,
                                                       indent=4))


def test_k8s_get_calico_status(local_salt_client):
    result = local_salt_client.cmd(
        'kubernetes:pool', 'cmd.run',
        ['calicoctl node status'],
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
    assert not errors, 'Calico node status is not good: {}'.format(json.dumps(
                                                                   errors,
                                                                   indent=4))


def test_k8s_cluster_status(local_salt_client):
    result = local_salt_client.cmd(
        'kubernetes:pool', 'cmd.run',
        ['kubectl cluster-info'],
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
    assert not errors, 'k8s cluster info is not good: {}'.format(json.dumps(
                                                                 errors,
                                                                 indent=4))


def test_k8s_kubelet_status(local_salt_client):
    result = local_salt_client.cmd(
        'kubernetes:pool', 'service.status',
        ['kubelet'],
        expr_form='pillar'
    )
    errors = []
    if not result:
        pytest.skip("k8s is not found on this environment")
    for node in result:
        if not result[node]:
            errors.append(node)
    assert not errors, 'Kublete is not running on these nodes: {}'.format(
                       errors)


def test_ping_host(local_salt_client):
    # not a test actually
    hostname = 'docker-dev-virtual.docker.mirantis.net'
    response = os.system('ping -c 1 ' + hostname)
    if response == 0:
        print '{} is AVAILABLE'.format(hostname)
    else:
        print '{} IS NOT AVAILABLE'.format(hostname)
