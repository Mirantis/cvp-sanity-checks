import json
import utils
import pytest


@pytest.mark.xfail
@pytest.mark.smoke
#move to sl?
def test_ntp_sync(local_salt_client):
    """Test checks that system time is the same across all nodes"""

    config = utils.get_configuration()
    nodes_time = local_salt_client.cmd(
        tgt='*',
        param='date +%s',
        expr_form='compound')
    result = {}
    for node, time in nodes_time.iteritems():
        if isinstance(nodes_time[node], bool):
            time = 'Cannot access node(-s)'
        if node in config.get("ntp_skipped_nodes"):
            continue
        if time in result:
            result[time].append(node)
            result[time].sort()
        else:
            result[time] = [node]
    assert len(result) <= 1, 'Not all nodes have the same time:\n {}'.format(
                             json.dumps(result, indent=4))


@pytest.mark.smoke
def test_ntp_peers_state(local_salt_client):
    """Test gets ntpq peers state and checks the system peer is declared"""
    state = local_salt_client.cmd(
        tgt='*',
        param='ntpq -pn',
        expr_form='compound')
    final_result = {}
    for node in state:
        sys_peer_declared = False
        if not state[node]:
            # TODO: do not skip
            print ("Node {} is skipped".format(node))
            continue
        ntpq_output = state[node].split('\n')
        # if output has no 'remote' in the head of ntpq output
        # the 'ntqp -np' command failed and cannot check peers
        if 'remote' not in ntpq_output[0]:
            final_result[node] = ntpq_output
            continue

        # take 3rd+ line of output (the actual peers)
        try:
            peers = ntpq_output[2:]
        except IndexError:
            final_result[node] = ntpq_output
            continue
        for p in peers:
            if p.split()[0].startswith("*"):
                sys_peer_declared = True
        if not sys_peer_declared:
            final_result[node] = ntpq_output
    assert not final_result,\
        "NTP peers state is not expected on some nodes, could not find " \
        "declared system peer:\n{}".format(json.dumps(final_result, indent=4))
