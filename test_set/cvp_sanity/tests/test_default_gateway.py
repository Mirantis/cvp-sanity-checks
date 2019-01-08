import json
import pytest
import os
from cvp_checks import utils


def test_check_default_gateways(local_salt_client, nodes_in_group):
    netstat_info = local_salt_client.cmd(
        "L@"+','.join(nodes_in_group), 'cmd.run', ['ip r | sed -n 1p'], expr_form='compound')

    gateways = {}
    nodes = netstat_info.keys()

    for node in nodes:
        if netstat_info[node] not in gateways:
            gateways[netstat_info[node]] = [node]
        else:
            gateways[netstat_info[node]].append(node)

    assert len(gateways.keys()) == 1, \
        "There were found few gateways: {gw}".format(
        gw=json.dumps(gateways, indent=4)
    )
