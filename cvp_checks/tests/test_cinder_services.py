import pytest


def test_cinder_services(local_salt_client):
    service_down = local_salt_client.cmd(
        'cinder:controller',
        'cmd.run',
        ['. /root/keystonerc; cinder service-list | grep "down\|disabled"'],
        expr_form='pillar')
    if not service_down:
        pytest.skip("Cinder is not found on this environment")
    cinder_volume = local_salt_client.cmd(
        'keystone:server',
        'cmd.run',
        ['. /root/keystonerc; cinder service-list | grep "volume" | wc -l'],
        expr_form='pillar')
    assert service_down[service_down.keys()[0]] == '', \
        '''Some cinder services are in wrong state'''
    assert int(cinder_volume[cinder_volume.keys()[0]]) >= 1, \
        '''There are less than 1 host/backend for cinder'''
