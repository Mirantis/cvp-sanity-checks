import pytest
import json

pytestmark = pytest.mark.usefixtures("contrail")

STATUS_FILTER = r'grep -Pv "(==|^$|Disk|unix|support|boot|\*\*|FOR NODE)"'
STATUS_COMMAND = "contrail-status -t 10"

def get_contrail_status(salt_client, pillar, command, processor):
    return salt_client.cmd(
        tgt=pillar,
        param='{} | {}'.format(command, processor),
        expr_form='pillar'
    )

@pytest.mark.sl_dup
#ContrailApiDown, ContrailApiDownMinor
@pytest.mark.full
def test_contrail_compute_status(local_salt_client, check_openstack):
    cs = get_contrail_status(local_salt_client, 'nova:compute',
                             STATUS_COMMAND, STATUS_FILTER)
    broken_services = []

    for node in cs:
        for line in cs[node].split('\n'):
            line = line.strip()
            if len (line.split(None, 1)) == 1:
                err_msg = "{0}: {1}".format(
                    node, line)
                broken_services.append(err_msg)
                continue
            name, status = line.split(None, 1)
            if status not in {'active'}:
                err_msg = "{node}:{service} - {status}".format(
                    node=node, service=name, status=status)
                broken_services.append(err_msg)

    assert not broken_services, (
        'Some Contrail services are in wrong state on computes: {}'.format(
            json.dumps(broken_services, indent=4))
    )

@pytest.mark.smoke
def test_contrail_node_status(local_salt_client, check_openstack):
    command = STATUS_COMMAND

    # TODO: what will be in OpenContrail 5?
    if pytest.contrail == '4':
        command = "doctrail all " + command
    cs = get_contrail_status(local_salt_client,
                             'opencontrail:client:analytics_node',
                             command, STATUS_FILTER)
    cs.update(get_contrail_status(local_salt_client, 'opencontrail:control',
                                  command, STATUS_FILTER)
    )
    broken_services = []
    for node in cs:
        for line in cs[node].split('\n'):
            line = line.strip()
            if 'crashes/core.java.' not in line:
                name, status = line.split(None, 1)
            else:
                name, status = line, 'FATAL'
            if status not in {'active', 'backup'}:
                err_msg = "{node}:{service} - {status}".format(
                    node=node, service=name, status=status)
                broken_services.append(err_msg)

    assert not broken_services, (
        'Some Contrail services are in wrong state on Contrail controllers: '
        '{}'.format(json.dumps(broken_services, indent=4))
    )

@pytest.mark.smoke
def test_contrail_vrouter_count(local_salt_client, check_openstack):
    cs = get_contrail_status(local_salt_client, 'nova:compute',
                             STATUS_COMMAND, STATUS_FILTER)

    # TODO: what if compute lacks these service unintentionally?
    if not cs:
        pytest.skip("Contrail services were not found on compute nodes")

    actual_vrouter_count = 0
    for node in cs:
        for line in cs[node].split('\n'):
            if 'contrail-vrouter-nodemgr' in line:
                actual_vrouter_count += 1

    assert actual_vrouter_count == len(list(cs.keys())),\
        'The length of vRouters {} differs' \
        ' from the length of compute nodes {}'.format(actual_vrouter_count,
                                                      len(list(cs.keys())))

@pytest.mark.smoke
def test_public_ui_contrail(local_salt_client, ctl_nodes_pillar, check_openstack):
    IP = local_salt_client.pillar_get(param='_param:cluster_public_host')
    protocol = 'https'
    port = '8143'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd_any(
        tgt=ctl_nodes_pillar,
        param='curl -k {}/ 2>&1 | \
               grep Contrail'.format(url))
    assert len(result) != 0, \
        'Public Contrail UI is not reachable on {} from ctl nodes'.format(url)
