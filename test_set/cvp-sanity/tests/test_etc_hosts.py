import json
import pytest


@pytest.mark.full
def test_etc_hosts(local_salt_client):
    nodes_info = local_salt_client.cmd(
        tgt='*',
        param='cat /etc/hosts',
        expr_form='compound')
    result = {}
    for node in list(nodes_info.keys()):
        if isinstance(nodes_info[node], bool):
            result[node] = 'Cannot access this node'
            continue
        for nd in list(nodes_info.keys()):
            if nd not in nodes_info[node]:
                if node in result:
                    result[node] += ',' + nd
                else:
                    result[node] = nd
    assert len(result) <= 1, \
        "Some hosts are not presented in /etc/hosts: {0}".format(
        json.dumps(result, indent=4))
