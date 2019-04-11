from collections import Counter
from pprint import pformat
import os

import utils


def get_duplicate_ifaces(nodes, ips):
    dup_ifaces = {}
    for node in nodes:
        for iface in nodes[node]['ip4_interfaces']:
            if set(nodes[node]['ip4_interfaces'][iface]) & set(ips):
                dup_ifaces[node] = {iface: nodes[node]['ip4_interfaces'][iface]}
    return dup_ifaces


def test_duplicate_ips(local_salt_client):
    testname = os.path.basename(__file__).split('.')[0]
    config = utils.get_configuration()
    skipped_ifaces = config.get(testname)["skipped_ifaces"]

    local_salt_client.cmd(tgt='*',
                          fun='saltutil.refresh_grains',
                          expr_form='compound')
    nodes = local_salt_client.cmd(tgt='*',
                                  fun='grains.item',
                                  param='ip4_interfaces',
                                  expr_form='compound')

    ipv4_list = []
    for node in nodes:
        if isinstance(nodes[node], bool):
            # TODO: do not skip node
            print ("{} node is skipped".format(node))
            continue
        for iface in nodes[node]['ip4_interfaces']:
            # Omit 'ip-less' ifaces
            if not nodes[node]['ip4_interfaces'][iface]:
                continue
            if iface in skipped_ifaces:
                continue
            ipv4_list.extend(nodes[node]['ip4_interfaces'][iface])
    no_dups = (len(ipv4_list) == len(set(ipv4_list)))
    if not no_dups:
        ips_count = Counter(ipv4_list).most_common()
        dup_ips = filter(lambda x: x[1] > 1, ips_count)
        dup_ifaces = get_duplicate_ifaces(nodes, [v[0] for v in dup_ips])

        msg = ("\nDuplicate IP addresses found:\n{}"
               "\n\nThe following interfaces are affected:\n{}"
                "".format(pformat(dup_ips), pformat(dup_ifaces)))
        assert no_dups, msg
