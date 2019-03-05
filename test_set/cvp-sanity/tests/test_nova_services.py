import pytest


@pytest.mark.usefixtures('check_openstack')
def test_nova_services_status(local_salt_client):
    result = local_salt_client.cmd(
        'keystone:server',
        'cmd.run',
        ['. /root/keystonercv3;'
         'nova service-list | grep "down\|disabled" | grep -v "Forced down"'],
        expr_form='pillar')

    assert result[result.keys()[0]] == '', \
        '''Some nova services are in wrong state'''


@pytest.mark.usefixtures('check_openstack')
def test_nova_hosts_consistent(local_salt_client):
    all_cmp_services = local_salt_client.cmd(
        'keystone:server',
        'cmd.run',
        ['. /root/keystonercv3;'
         'nova service-list | grep "nova-compute" | wc -l'],
        expr_form='pillar').values()[0]
    enabled_cmp_services = local_salt_client.cmd(
        'keystone:server',
        'cmd.run',
        ['. /root/keystonercv3;'
         'nova service-list | grep "nova-compute" | grep "enabled" | wc -l'],
        expr_form='pillar').values()[0]
    hosts = local_salt_client.cmd(
        'keystone:server',
        'cmd.run',
        ['. /root/keystonercv3;'
         'openstack host list | grep "compute" | wc -l'],
        expr_form='pillar').values()[0]
    hypervisors = local_salt_client.cmd(
        'keystone:server',
        'cmd.run',
        ['. /root/keystonercv3;'
         'openstack hypervisor list | egrep -v "\-----|ID" | wc -l'],
        expr_form='pillar').values()[0]

    assert all_cmp_services == hypervisors, \
        "Number of nova-compute services ({}) does not match number of " \
        "hypervisors ({}).".format(all_cmp_services, hypervisors)
    assert enabled_cmp_services == hosts, \
        "Number of enabled nova-compute services ({}) does not match number \
        of hosts ({}).".format(enabled_cmp_services, hosts)
