import json
import pytest


def test_ceph_osd(local_salt_client):
    osd_fail = local_salt_client.cmd(
        tgt='ceph:osd',
        param='ceph osd tree | grep down',
        expr_form='pillar')
    if not osd_fail:
        pytest.skip("Ceph is not found on this environment")
    assert not osd_fail.values()[0], (
        "Some OSDs are in down state:\n{}".format(osd_fail.values()[0]))


def test_ceph_health(local_salt_client):
    get_status = local_salt_client.cmd(
        tgt='ceph:mon',
        param='ceph -s -f json',
        expr_form='pillar')
    if not get_status:
        pytest.skip("Ceph is not found on this environment")
    status = json.loads(get_status.values()[0])["health"]
    health = status["status"] if 'status' in status \
        else status["overall_status"]

    # Health structure depends on Ceph version, so condition is needed:
    if 'checks' in status:
        summary = "Summary: {}".format(
            [i["summary"]["message"] for i in status["checks"].values()])
    else:
        summary = status["summary"]

    assert health == "HEALTH_OK", "Ceph is not healthy:\n{}".format(summary)
