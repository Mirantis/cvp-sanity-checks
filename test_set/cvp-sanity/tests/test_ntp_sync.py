import utils
import os


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
