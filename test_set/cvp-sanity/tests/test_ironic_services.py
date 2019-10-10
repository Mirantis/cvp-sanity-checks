import pytest


@pytest.mark.full
@pytest.mark.usefixtures('check_ironic')
@pytest.mark.usefixtures('check_openstack')
def test_ironic_nodes_are_available_or_active(local_salt_client):
    """
        Make sure that ironic nodes are available or active - check that all
        nodes have 'active' or 'available' state in output of
        `openstack baremetal node list` on 'keystone:server' nodes.
        The other states are not expected. See full states description:
        https://docs.openstack.org/ironic/latest/contributor/states.html
    """
    result = local_salt_client.cmd_any(
        tgt='keystone:server',
        param='. /root/keystonercv3; openstack baremetal node list | '
              'grep -v "\-------\|UUID\|active\|available"')
    assert result == '', (
        "Some Ironic nodes are in wrong state:\n{}".format(result))
