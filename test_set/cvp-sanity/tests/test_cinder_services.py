import pytest


def test_cinder_services(local_salt_client):
    """
        # Make sure that cinder backend exists with next command: `salt -C "I@cinder:controller" pillar.get cinder:controller:backend`
        # Check that all services has 'Up' status in output of `cinder service-list` on keystone:server nodes
        # Check that quantity of backend in cinder:controller:backend pillar is similar to list of volumes in cinder service-list
    """
    backends_cinder = local_salt_client.test_ping(tgt='cinder:controller:backend')
    if not backends_cinder or not any(backends_cinder.values()):
        pytest.skip("Cinder service or cinder:controller:backend pillar \
        are not found on this environment.")
    service_down = local_salt_client.cmd_any(
        tgt='keystone:server',
        param='. /root/keystonercv3; cinder service-list | grep "down\|disabled"')
    cinder_volume = local_salt_client.cmd_any(
        tgt='keystone:server',
        param='. /root/keystonercv3; cinder service-list | grep -c "volume"')
    backends_num = len(backends_cinder.keys())
    assert service_down == '', \
        '''Some cinder services are in wrong state'''
    assert cinder_volume == str(backends_num), \
        'Number of cinder-volume services ({0}) does not match ' \
        'number of volume backends ({1})'.format(
        cinder_volume, str(backends_num))
