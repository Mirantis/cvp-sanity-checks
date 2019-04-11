import pytest


def test_ceph_replicas(local_salt_client):
    """
    Test aimed to check number of replicas
    for most of deployments if there is no
    special requirement for that.
    """

    ceph_monitors = local_salt_client.test_ping(tgt='ceph:mon')

    if not ceph_monitors:
        pytest.skip("Ceph is not found on this environment")

    monitor = ceph_monitors.keys()[0]

    raw_pool_replicas = local_salt_client.cmd_any(
        tgt='ceph:mon',
        param="ceph osd dump | grep size | " \
              "awk '{print $3, $5, $6, $7, $8}'").split('\n')

    pools_replicas = {}
    for pool in raw_pool_replicas:
        pool_name = pool.split(" ", 1)[0]
        pool_replicas = {}
        raw_replicas = pool.split(" ", 1)[1].split()
        for elem in raw_replicas:
            pool_replicas[raw_replicas[0]] = int(raw_replicas[1])
            pool_replicas[raw_replicas[2]] = int(raw_replicas[3])
        pools_replicas[pool_name] = pool_replicas
    
    error = []
    for pool, replicas in pools_replicas.items():
        for replica, value in replicas.items():
            if replica == 'min_size' and value < 2:
                error.append(pool + " " + replica + " " 
                + str(value) + " must be 2")
            if replica == 'size' and value < 3:
                error.append(pool + " " + replica + " " 
                + str(value) + " must be 3")
    
    assert not error, "Wrong pool replicas found\n{}".format(error)
