import pytest
import json
import utils
import os
import logging


@pytest.mark.full
def test_mtu(local_salt_client, nodes_in_group):
    testname = os.path.basename(__file__).split('.')[0]
    config = utils.get_configuration()
    skipped_ifaces = config.get(testname)["skipped_ifaces"] or \
        ["bonding_masters", "lo", "veth", "tap", "cali", "qv", "qb", "br-int",
         "vxlan", "virbr0", "virbr0-nic", "docker0", "o-hm0"]
    group, nodes = nodes_in_group
    total = {}
    network_info = local_salt_client.cmd(
        tgt="L@"+','.join(nodes),
        param='ls /sys/class/net/',
        expr_form='compound')

    if len(list(network_info.keys())) < 2:
        pytest.skip("Nothing to compare - only 1 node")

    # collect all nodes and check if virsh is installed there
    kvm_nodes = local_salt_client.cmd(
        tgt='salt:control',
        fun='pkg.version',
        param='libvirt-clients',
        expr_form='pillar'
    )

    for node, ifaces_info in network_info.items():
        if isinstance(ifaces_info, bool):
            logging.info("{} node skipped. No interfaces available.".format(node))
            continue
        # if node is a kvm node and virsh is installed there
        if node in list(kvm_nodes.keys()) and kvm_nodes[node]:
            domain_name = node.split(".", 1)[1]
            # vms_count calculated separately to have readable output
            # and for further debug if needed
            vms_count = local_salt_client.cmd(tgt=node, param="virsh list | grep {}"
                                              .format(domain_name))
            if not vms_count[node]:
                logging.info("{} node skipped. No OS vm's running.".format(node))
                continue
            # param assumes that KVM has OS vm's running.
            # virsh list | grep domain_name --- fails
            # if KVM has nothing to grep and test fails
            param = "virsh list | grep " + domain_name + "| awk '{print $2}' | " \
                                                         "xargs -n1 virsh domiflist | " \
                                                         "grep -v br-pxe | grep br- | " \
                                                         "awk '{print $1}' "
            kvm_info = local_salt_client.cmd(tgt=node, param=param)
            ifaces_info = kvm_info.get(node)
        node_ifaces = ifaces_info.split('\n')
        ifaces = {}
        for iface in node_ifaces:
            for skipped_iface in skipped_ifaces:
                if skipped_iface in iface:
                    break
            else:
                iface_mtu = local_salt_client.cmd(tgt=node,
                                                  param='cat /sys/class/'
                                                        'net/{}/mtu'.format(iface))
                ifaces[iface] = iface_mtu.get(node)
        total[node] = ifaces

    nodes = []
    mtu_data = []
    my_set = set()

    for node in total:
        nodes.append(node)
        my_set.update(list(total[node].keys()))
    for interf in my_set:
        diff = []
        row = []
        for node in nodes:
            if interf in list(total[node].keys()):
                diff.append(total[node][interf])
                row.append("{}: {}".format(node, total[node][interf]))
            else:
                row.append("{}: No interface".format(node))
        if diff.count(diff[0]) < len(nodes):
            row.sort()
            row.insert(0, interf)
            mtu_data.append(row)
    assert len(mtu_data) == 0, (
        "Non-uniform MTUs are set on the same node interfaces of '{}' group "
        "of nodes: {}".format(group, json.dumps(mtu_data, indent=4))
    )
