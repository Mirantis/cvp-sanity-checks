import pytest


def test_ceph_haproxy(local_salt_client):
    pytest.skip("This test doesn't work. Skipped")
    fail = {}

    monitor_info = local_salt_client.cmd(
        'ceph:mon',
        'cmd.run',
        ["echo 'show stat' | nc -U "
         "/var/run/haproxy/admin.sock | "
         "grep ceph_mon_radosgw_cluster"],
        expr_form='pillar')
    if not monitor_info:
        pytest.skip("Ceph is not found on this environment")

    for name, info in monitor_info.iteritems():
        if "OPEN" and "UP" in info:
            continue
        else:
            fail[name] = info
    assert not fail, "Failed monitors: {}".format(fail)
