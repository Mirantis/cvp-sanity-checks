import pytest
import json
import os
from cvp_checks import utils


def test_check_services(local_salt_client, nodes_in_group):
    output = local_salt_client.cmd("L@"+','.join(nodes_in_group), 'service.get_all', expr_form='compound')

    if len(output.keys()) < 2:
        pytest.skip("Nothing to compare - only 1 node")

    nodes = []
    pkts_data = []
    my_set = set()

    for node in output:
        nodes.append(node)
        my_set.update(output[node])

    for srv in my_set:
        diff = []
        row = []
        for node in nodes:
            if srv in output[node]:
                diff.append(srv)
                row.append("{}: +".format(node))
            else:
                row.append("{}: No service".format(node))
        if diff.count(diff[0]) < len(nodes):
            row.sort()
            row.insert(0, srv)
            pkts_data.append(row)
    assert len(pkts_data) <= 1, \
        "Several problems found: {0}".format(
        json.dumps(pkts_data, indent=4))
