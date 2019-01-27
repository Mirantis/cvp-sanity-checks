import json
import pytest

from cvp_sanity import utils


def test_nodes_deployed_in_maas(local_salt_client):
    config = utils.get_configuration()
    get_apis = local_salt_client.cmd(
        'maas:cluster',
        'cmd.run',
        ['maas list'],
        expr_form='pillar')
    if not get_apis:
        pytest.skip("Could not find MAAS on the environment")
    profile = get_apis.values()[0].split(' ')[0]
    get_nodes = local_salt_client.cmd('maas:cluster', 'cmd.run',
                                      ['maas {} nodes read'.format(profile)],
                                      expr_form='pillar')
    result = ""
    try:
        result = json.loads(get_nodes.values()[0])
    except Exception as e:
        assert result, "Could not get nodes: {}\n{}".\
            format(get_nodes.values()[0], e)

    failed_nodes = []
    for node in result:
        if node["fqdn"] in config.get("skipped_nodes"):
            continue
        if "status_name" in node.keys():
            if node["status_name"] != 'Deployed':
                failed_nodes.append({node["fqdn"]: node["status_name"]})
    assert not failed_nodes, "Some nodes have unexpected status in MAAS:" \
                             "\n{}".format(failed_nodes)
