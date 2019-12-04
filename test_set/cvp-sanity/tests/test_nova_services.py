import pytest


@pytest.mark.sl_dup
@pytest.mark.full
@pytest.mark.usefixtures('check_openstack')
def test_nova_services_status(local_salt_client):
    result = local_salt_client.cmd_any(
        tgt='keystone:server',
        param='. /root/keystonercv3;'
              'nova service-list | grep "down\|disabled" | grep -v "Forced down"')

    assert result == '', (
        "Some Nova services are in wrong state:\n{}".format(result))


@pytest.mark.smoke
@pytest.mark.usefixtures('check_openstack')
def test_nova_hosts_consistent(local_salt_client):
    # exclude bmt* nodes because they also have nova-compute running
    # but they are not the hypervisors
    ironic = local_salt_client.test_ping(tgt='ironic:client')
    if ironic:
        ironic_nodes = [i.split('.')[0] for i in ironic]
        grep_exclude_ironic = "| egrep -v '{}'".format("|".join(ironic_nodes))
    else:
        grep_exclude_ironic = ""

    all_cmp_services = local_salt_client.cmd_any(
        tgt='keystone:server',
        param='. /root/keystonercv3;'
              'nova service-list | grep "nova-compute" '
              '{} | wc -l'.format(grep_exclude_ironic))
    enabled_cmp_services = local_salt_client.cmd_any(
        tgt='keystone:server',
        param='. /root/keystonercv3;'
              'nova service-list | grep "nova-compute" | grep "enabled" '
              '{} | wc -l'.format(grep_exclude_ironic))
    hosts = local_salt_client.cmd_any(
        tgt='keystone:server',
        param='. /root/keystonercv3;'
              'openstack host list | grep "compute" '
              '{} | wc -l'.format(grep_exclude_ironic))
    hypervisors = local_salt_client.cmd_any(
        tgt='keystone:server',
        param='. /root/keystonercv3;'
              'openstack hypervisor list | egrep -v "\-----|ID" '
              '{} | wc -l'.format(grep_exclude_ironic))

    assert all_cmp_services == hypervisors, (
        "Number of nova-compute services ({}) does not match number of "
        "hypervisors ({}).".format(all_cmp_services, hypervisors)
    )
    assert enabled_cmp_services == hosts, (
        "Number of enabled nova-compute services ({}) does not match number "
        "of hosts ({}).".format(enabled_cmp_services, hosts)
    )
