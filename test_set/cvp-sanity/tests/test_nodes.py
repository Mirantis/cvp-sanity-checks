import json
import pytest


def test_minions_status(local_salt_client):
    result = local_salt_client.cmd(
        'salt:master',
        'cmd.run',
        ['salt-run manage.status timeout=10 --out=json'],
        expr_form='pillar')
    statuses = {}
    try:
        statuses = json.loads(result.values()[0])
    except Exception as e:
        pytest.fail(
            "Could not check the result: {}\n"
            "Nodes status result: {}".format(e, result))
    assert not statuses["down"], "Some minions are down:\n {}".format(
        statuses["down"])