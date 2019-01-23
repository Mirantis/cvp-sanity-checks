import pytest
import json
import utils
import os


def test_mtu(local_salt_client, nodes_in_group):
    testname = os.path.basename(__file__).split('.')[0]
    config = utils.get_configuration()
    skipped_ifaces = config.get(testname)["skipped_ifaces"] or \
        ["bonding_masters", "lo", "veth", "tap", "cali", "qv", "qb", "br-int", "vxlan"]
    total = {}
    network_info = local_salt_client.cmd(
        "L@"+','.join(nodes_in_group), 'cmd.run', ['ls /sys/class/net/'], expr_form='compound')

    kvm_nodes = local_salt_client.cmd(
        'salt:control', 'test.ping', expr_form='pillar').keys()

    if len(network_info.keys()) < 2:
        pytest.skip("Nothing to compare - only 1 node")

    for node, ifaces_info in network_info.iteritems():
        if node in kvm_nodes:
            kvm_info = local_salt_client.cmd(node, 'cmd.run',
                                             ["virsh list | "
                                              "awk '{print $2}' | "
                                              "xargs -n1 virsh domiflist | "
                                              "grep -v br-pxe | grep br- | "
                                              "awk '{print $1}'"])
            ifaces_info = kvm_info.get(node)
        node_ifaces = ifaces_info.split('\n')
        ifaces = {}
        for iface in node_ifaces:
            for skipped_iface in skipped_ifaces:
                if skipped_iface in iface:
                    break
            else:
                iface_mtu = local_salt_client.cmd(node, 'cmd.run',
                                                  ['cat /sys/class/'
                                                   'net/{}/mtu'.format(iface)])
                ifaces[iface] = iface_mtu.get(node)
        total[node] = ifaces

    nodes = []
    mtu_data = []
    my_set = set()

    for node in total:
        nodes.append(node)
        my_set.update(total[node].keys())
    for interf in my_set:
        diff = []
        row = []
        for node in nodes:
            if interf in total[node].keys():
                diff.append(total[node][interf])
                row.append("{}: {}".format(node, total[node][interf]))
            else:
                row.append("{}: No interface".format(node))
        if diff.count(diff[0]) < len(nodes):
            row.sort()
            row.insert(0, interf)
            mtu_data.append(row)
    assert len(mtu_data) == 0, \
        "Several problems found: {0}".format(
        json.dumps(mtu_data, indent=4))
