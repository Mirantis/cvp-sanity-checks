import utils
import json


def test_single_vip_exists(local_salt_client):
    """Test checks that there is only one VIP address
       within one group of nodes (where applicable).
       Steps:
       1. Get IP addresses for nodes via salt cmd.run 'ip a | grep /32'
       2. Check that at least 1 node responds with something.
    """
    groups = utils.calculate_groups()
    no_vip = {}
    for group in groups:
        if group in ['cmp', 'cfg', 'kvm', 'cmn', 'osd', 'gtw']:
            continue
        nodes_list = local_salt_client.cmd(
            "L@" + ','.join(groups[group]), 'cmd.run', 'ip a | grep /32', expr_form='compound')
        result = [x for x in nodes_list.values() if x]
        if len(result) != 1:
            if len(result) == 0:
                no_vip[group] = 'No vip found'
            else:
                no_vip[group] = nodes_list
    assert len(no_vip) < 1, "Some groups of nodes have problem with vip " \
           "\n{}".format(json.dumps(no_vip, indent=4))
