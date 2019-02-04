import json
import os

import utils


def test_ntp_sync(local_salt_client):
    testname = os.path.basename(__file__).split('.')[0]
    active_nodes = utils.get_active_nodes(os.path.basename(__file__))
    config = utils.get_configuration()
    fail = {}
    saltmaster_time = int(local_salt_client.cmd(
        'salt:master',
        'cmd.run',
        ['date +%s'],
        expr_form='pillar').values()[0])
    nodes_time = local_salt_client.cmd(
        utils.list_to_target_string(active_nodes, 'or'),
        'cmd.run',
        ['date +%s'],
        expr_form='compound')
    diff = config.get(testname)["time_deviation"] or 30
    for node, time in nodes_time.iteritems():
        if (int(time) - saltmaster_time) > diff or \
                (int(time) - saltmaster_time) < -diff:
            fail[node] = time

    assert not fail, 'SaltMaster time: {}\n' \
                     'Nodes with time mismatch:\n {}'.format(saltmaster_time,
                                                             fail)


def test_ntp_peers_state(local_salt_client):
    """Test gets ntpq peers state and check the system peer is declared"""

    active_nodes = utils.get_active_nodes(os.path.basename(__file__))
    state = local_salt_client.cmd(
        utils.list_to_target_string(active_nodes, 'or'),
        'cmd.run',
        ['ntpq -pn'],
        expr_form='compound')
    final_result = {}
    for node in state:
        sys_peer_declared = False
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
