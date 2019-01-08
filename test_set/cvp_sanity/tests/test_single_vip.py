import pytest
from cvp_checks import utils
import os
from collections import Counter


def test_single_vip(local_salt_client, nodes_in_group):
    local_salt_client.cmd("L@"+','.join(nodes_in_group), 'saltutil.sync_all', expr_form='compound')
    nodes_list = local_salt_client.cmd(
        "L@"+','.join(nodes_in_group), 'grains.item', ['ipv4'], expr_form='compound')

    ipv4_list = []

    for node in nodes_list:
        ipv4_list.extend(nodes_list.get(node).get('ipv4'))

    cnt = Counter(ipv4_list)

    for ip in cnt:
        if ip == '127.0.0.1':
            continue
        elif cnt[ip] > 1:
            assert "VIP IP duplicate found " \
                   "\n{}".format(ipv4_list)
