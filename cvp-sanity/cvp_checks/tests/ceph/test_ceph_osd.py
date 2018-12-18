import pytest


def test_check_ceph_osd(local_salt_client):
    osd_fail = local_salt_client.cmd(
        'ceph:osd',
        'cmd.run',
        ['ceph osd tree | grep down'],
        expr_form='pillar')
    if not osd_fail:
        pytest.skip("Ceph is not found on this environment")
    assert not osd_fail.values()[0], \
        "Some osds are in down state or ceph is not found".format(
        osd_fail.values()[0])
