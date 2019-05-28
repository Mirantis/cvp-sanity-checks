import json
import pytest


@pytest.mark.smoke
#full?
def test_mounted_file_systems(local_salt_client, nodes_in_group):
    """
        # Get all mount points from each node in the group  with the next command: `df -h | awk '{print $1}'`
        # Check that all mount points are similar for each node in the group
    """
    exclude_mounts = 'grep -v "overlay\|tmpfs\|shm\|Filesystem"'
    mounts_by_nodes = local_salt_client.cmd(tgt="L@"+','.join(nodes_in_group),
                                            param="df -h | awk '{print $1}'" +
                                                  " |" + exclude_mounts,
                                            expr_form='compound')

    # Let's exclude cmp, kvm, ceph OSD nodes, mon, cid, k8s-ctl, k8s-cmp nodes
    # These nodes will have different mounts and this is expected
    exclude_nodes = local_salt_client.test_ping(
         tgt="I@nova:compute or "
             "I@ceph:osd or "
             "I@salt:control or "
             "I@prometheus:server and not I@influxdb:server or "
             "I@kubernetes:* and not I@etcd:* or "
             "I@docker:host and not I@prometheus:server and not I@kubernetes:* or "
             "I@gerrit:client and I@kubernetes:pool and not I@salt:master",
         expr_form='compound').keys()

    if len(mounts_by_nodes.keys()) < 2:
        pytest.skip("Nothing to compare - only 1 node")

    result = {}
    pretty_result = {}

    for node in mounts_by_nodes:
        if node in exclude_nodes:
            continue
        if isinstance(mounts_by_nodes[node], bool):
            result[node] = 'Cannot access this node'
            pretty_result[node] = 'Cannot access this node'
        else:
            result[node] = "\n".join(sorted(mounts_by_nodes[node].split()))
            pretty_result[node] = sorted(mounts_by_nodes[node].split())

    if not result:
        pytest.skip("These nodes are skipped")

    assert len(set(result.values())) == 1,\
        "The nodes in the same group have different mounts:\n{}".format(
            json.dumps(pretty_result, indent=4))
