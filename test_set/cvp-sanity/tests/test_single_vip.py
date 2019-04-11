from collections import Counter


def test_single_vip(local_salt_client, nodes_in_group):
    local_salt_client.cmd(tgt="L@"+','.join(nodes_in_group),
                          fun='saltutil.sync_all',
                          expr_form='compound')
    nodes_list = local_salt_client.cmd(
        tgt="L@"+','.join(nodes_in_group),
        fun='grains.item',
        param='ipv4',
        expr_form='compound')

    ipv4_list = []

    for node in nodes_list:
        if not nodes_list.get(node):
            # TODO: do not skip node
            print "Node {} is skipped".format (node)
            continue
        ipv4_list.extend(nodes_list.get(node).get('ipv4'))

    cnt = Counter(ipv4_list)

    for ip in cnt:
        if ip == '127.0.0.1':
            continue
        elif cnt[ip] > 1:
            assert "VIP IP duplicate found " \
                   "\n{}".format(ipv4_list)
