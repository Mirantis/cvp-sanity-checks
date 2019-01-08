import pytest
import math

def __next_power_of2(total_pg):
	count = 0
	if (total_pg and not(total_pg & (total_pg - 1))):
		return total_pg	
	while( total_pg != 0):
		total_pg >>= 1
		count += 1
	
	return 1 << count


def test_ceph_pg_count(local_salt_client):
    """
    Test aimed to calculate placement groups for Ceph cluster
    according formula below.
    Formula to calculate PG num:
    Total PGs = 
    (Total_number_of_OSD * 100) / max_replication_count / pool count
    pg_num and pgp_num should be the same and 
    set according formula to higher value of powered 2
    """
    pytest.skip("This test needs redesign. Skipped for now")
    ceph_monitors = local_salt_client.cmd(
        'ceph:mon', 
        'test.ping', 
        expr_form='pillar')
    
    if not ceph_monitors:
        pytest.skip("Ceph is not found on this environment")

    monitor = ceph_monitors.keys()[0]
    pools = local_salt_client.cmd(
        monitor, 'cmd.run', 
        ["rados lspools"], 
        expr_form='glob').get(
            ceph_monitors.keys()[0]).split('\n')
    
    total_osds = int(local_salt_client.cmd(
        monitor, 
        'cmd.run', 
        ['ceph osd tree | grep osd | grep "up\|down" | wc -l'], 
        expr_form='glob').get(ceph_monitors.keys()[0]))
    
    raw_pool_replications = local_salt_client.cmd(
        monitor, 
        'cmd.run', 
        ["ceph osd dump | grep size | awk '{print $3, $6}'"], 
        expr_form='glob').get(ceph_monitors.keys()[0]).split('\n')
    
    pool_replications = {}
    for replication in raw_pool_replications:
        pool_replications[replication.split()[0]] = int(replication.split()[1])
    
    max_replication_value = 0
    for repl_value in pool_replications.values():
        if repl_value > max_replication_value:
            max_replication_value = repl_value

    total_pg = (total_osds * 100) / max_replication_value / len(pools)
    correct_pg_num = __next_power_of2(total_pg)
    
    pools_pg_num = {}
    pools_pgp_num = {}
    for pool in pools:
        pg_num = int(local_salt_client.cmd(
            monitor, 
            'cmd.run', 
            ["ceph osd pool get {} pg_num".format(pool)], 
            expr_form='glob').get(ceph_monitors.keys()[0]).split()[1])
        pools_pg_num[pool] = pg_num
        pgp_num = int(local_salt_client.cmd(
            monitor, 
            'cmd.run', 
            ["ceph osd pool get {} pgp_num".format(pool)], 
            expr_form='glob').get(ceph_monitors.keys()[0]).split()[1])
        pools_pgp_num[pool] = pgp_num

    wrong_pg_num_pools = [] 
    pg_pgp_not_equal_pools = []
    for pool in pools:
        if pools_pg_num[pool] != pools_pgp_num[pool]:
            pg_pgp_not_equal_pools.append(pool)
        if pools_pg_num[pool] < correct_pg_num:
            wrong_pg_num_pools.append(pool)

    assert not pg_pgp_not_equal_pools, \
    "For pools {} PG and PGP are not equal " \
    "but should be".format(pg_pgp_not_equal_pools)
    assert not wrong_pg_num_pools, "For pools {} " \
    "PG number lower than Correct PG number, " \
    "but should be equal or higher".format(wrong_pg_num_pools)
