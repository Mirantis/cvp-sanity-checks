from cvp_checks import utils
import json
import pytest

@pytest.mark.xfail
def test_ntp_sync(local_salt_client):
    """Test checks that system time is the same across all nodes"""

    active_nodes = utils.get_active_nodes()
    config = utils.get_configuration()
    nodes_time = local_salt_client.cmd(
        utils.list_to_target_string(active_nodes, 'or'),
        'cmd.run',
        ['date +%s'],
        expr_form='compound')
    result = {}
    for node, time in nodes_time.iteritems():
        if node in config.get("ntp_skipped_nodes"):
            continue
        if time in result:
            result[time].append(node)
            result[time].sort()
        else:
            result[time] = [node]
    assert len(result) <= 1, 'Not all nodes have the same time:\n {}'.format(
                             json.dumps(result, indent=4))
