import utils
import json
import pytest
import re


@pytest.mark.smoke
def test_single_vip_exists(local_salt_client):
    """Test checks that there is only one VIP address
       within one group of nodes (where applicable).
       Steps:
       1. Get IP addresses for nodes via salt cmd.run 'ip a | grep /32'
       2. Check that exactly 1 node responds with something.
    """
    groups = utils.calculate_groups()

    keywords_to_exclude_interfaces = ["flannel.1"]
    exclude_from_grep =  " | grep -v {}".format('\|'.join(keywords_to_exclude_interfaces)) \
                        if len(keywords_to_exclude_interfaces) > 0 \
                        else ""

    # Let's exclude cmp, kvm, ceph OSD nodes, k8s-cmp, cfg, apt, dns,
    # gtw, ceph mon nodes
    exclude_nodes = list(local_salt_client.test_ping(
         tgt="I@nova:compute or "                 # cmp
             "I@ceph:osd or "                     # ceph osd
             "I@salt:control or "                 # kvm
             "I@ceph:mon or "                     # ceph mon
             "I@salt:master or "                  # cfg
             "I@neutron:gateway or "              # gtw
             "I@powerdns:server or I@bind:server or "  # dns
             "I@debmirror:client or "             # apt
             "I@kubernetes:* and not I@etcd:*",   # k8s-cmp
         expr_form='compound').keys())

    # bmk nodes has no unique pillar, let's add it separately to skip
    bmk_hostname = local_salt_client.pillar_get(
        param='_param:openstack_benchmark_node01_hostname')
    if bmk_hostname:
        exclude_nodes.append(bmk_hostname)

    exclude_groups = []
    for node in exclude_nodes:
        index = re.search('[0-9]{1,3}$', node.split('.')[0])
        if index:
            exclude_groups.append(node.split('.')[0][:-len(index.group(0))])
        else:
            exclude_groups.append(node)
    no_vip = {}
    for group in groups:
        if group in exclude_groups:
            continue
        nodes_list = local_salt_client.cmd(
            tgt="L@" + ','.join(groups[group]),
            fun='cmd.run',
            param='ip a | grep /32 ' + exclude_from_grep,
            expr_form='compound')
        result = [x for x in list(nodes_list.values()) if x]
        if len(result) != 1:
            if len(result) == 0:
                no_vip[group] = 'No vip found'
            else:
                no_vip[group] = nodes_list
    assert len(no_vip) < 1, (
        "The following group(s) of nodes have problem with vip:\n{}".format(
            json.dumps(no_vip, indent=4))
    )
