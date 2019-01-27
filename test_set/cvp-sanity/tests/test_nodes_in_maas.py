import json
import pytest

import utils


def get_maas_logged_in_profiles(local_salt_client):
    get_apis = local_salt_client.cmd(
        'maas:cluster',
        'cmd.run',
        ['maas list'],
        expr_form='pillar')
    return get_apis.values()[0]


def login_to_maas(local_salt_client, user):
    login = local_salt_client.cmd(
        'maas:cluster',
        'cmd.run',
        ["source /var/lib/maas/.maas_login.sh  ; echo {}=${{PROFILE}}"
         "".format(user)],
        expr_form='pillar')
    return login.values()[0]


def test_nodes_deployed_in_maas(local_salt_client):
    config = utils.get_configuration()

    # 1. Check MAAS is present on some node
    check_maas = local_salt_client.cmd(
        'maas:cluster',
        'test.ping',
        expr_form='pillar')
    if not check_maas:
        pytest.skip("Could not find MAAS on the environment")

    # 2. Get MAAS admin user from model
    maas_admin_user = local_salt_client.cmd(
        'maas:cluster', 'pillar.get',
        ['_param:maas_admin_username'],
        expr_form='pillar'
    ).values()[0]
    if not maas_admin_user:
        pytest.skip("Could not find MAAS admin user in the model by parameter "
                    "'maas_admin_username'")

    # 3. Check maas has logged in profiles and try to log in if not
    logged_profiles = get_maas_logged_in_profiles(local_salt_client)
    if maas_admin_user not in logged_profiles:
        login = login_to_maas(local_salt_client, maas_admin_user)
        newly_logged = get_maas_logged_in_profiles(local_salt_client)
        if maas_admin_user not in newly_logged:
            pytest.skip(
                "Could not find '{}' profile in MAAS and could not log in.\n"
                "Current MAAS logged in profiles: {}.\nLogin output: {}"
                "".format(maas_admin_user, newly_logged, login))

    # 4. Get nodes in MAAS
    get_nodes = local_salt_client.cmd(
        'maas:cluster',
        'cmd.run',
        ['maas {} nodes read'.format(maas_admin_user)],
        expr_form='pillar')
    result = ""
    try:
        result = json.loads(get_nodes.values()[0])
    except ValueError as e:
        assert result, "Could not get nodes: {}\n{}". \
            format(get_nodes, e)

    # 5. Check all nodes are in Deployed status
    failed_nodes = []
    for node in result:
        if node["fqdn"] in config.get("skipped_nodes"):
            continue
        if "status_name" in node.keys():
            if node["status_name"] != 'Deployed':
                failed_nodes.append({node["fqdn"]: node["status_name"]})
    assert not failed_nodes, "Some nodes have unexpected status in MAAS:" \
                             "\n{}".format(json.dumps(failed_nodes, indent=4))
