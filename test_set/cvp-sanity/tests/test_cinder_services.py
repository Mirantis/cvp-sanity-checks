import pytest
import logging


@pytest.mark.sl_dup
#CinderServiceDown, CinderServicesDownMinor
@pytest.mark.full
def test_cinder_services_are_up(local_salt_client, check_cinder_backends):
    """
        # Make sure that cinder backend exists with next command: `salt -C "I@cinder:controller" pillar.get cinder:controller:backend`
        # Check that all services has 'Up' status in output of `cinder service-list` on keystone:server nodes
    """
    service_down = local_salt_client.cmd_any(
        tgt='keystone:server',
        param='. /root/keystonercv3; cinder service-list | grep "down\|disabled"')
    assert service_down == '', (
        "Some Cinder services are in wrong state:\n{}".format(service_down))


@pytest.mark.full
def test_cinder_services_has_all_backends(local_salt_client, check_cinder_backends):
    """
        # Make sure that cinder backend exists with next command: `salt -C "I@cinder:controller" pillar.get cinder:controller:backend`
        # Check that quantity of backend in cinder:controller:backend pillar is similar to list of volumes in cinder service-list
    """
    backends_cinder = local_salt_client.pillar_get(
        tgt='cinder:controller',
        param='cinder:controller:backend'
    )
    cinder_volume = local_salt_client.cmd_any(
        tgt='keystone:server',
        param='. /root/keystonercv3; cinder service-list | grep "volume" |grep -c -v -e "lvm"')
    backends_num = len(backends_cinder.keys())
    assert cinder_volume == str(backends_num), (
        'Number of cinder-volume services ({0}) does not match number of '
        'volume backends ({1}).'.format(cinder_volume, str(backends_num))
    )
