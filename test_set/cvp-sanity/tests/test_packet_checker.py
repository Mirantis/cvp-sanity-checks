import pytest
import json
import utils
import logging
import itertools
from functools import lru_cache


@lru_cache(maxsize=32)
def targeted_minions(target):
    """
    Returns nodes associated with salt target
    :param target: str, salt target in COMPOUND notation like I@nova:server
    More here https://docs.saltproject.io/en/latest/topics/targeting/compound.html
    :return: list of nodes or []
    """
    salt_client = pytest.local_salt_client
    return list(salt_client.test_ping(
        tgt=target,
        expr_form='compound'))


def is_deb_in_exception(inconsistency_rule, package_name, node_hostname):
    for salt_target, excluded_packages in inconsistency_rule.items():
        if package_name in excluded_packages \
                and node_hostname in targeted_minions(salt_target):
            return True
    return False


@pytest.mark.full
def test_check_package_versions(local_salt_client, nodes_in_group):
    """Validate package has same versions on all the nodes.
    Steps:
     1) Collect packages for nodes_in_group
        "salt -C '<group_of_nodes>' cmd.run 'lowpkg.list_pkgs'"
     2) Exclude nodes without packages and exceptions
     3) Go through each package and save it with version from each node to the
        list. Mark 'No version' if package is not found.
        If package name in the exception list or in inconsistency_rule,
        ignore it.
     4) Compare items in that list - they should be equal and match the amout of nodes

    """
    salt = local_salt_client
    # defines packages specific to the nodes
    inconsistency_rule = {
        "I@backupninja:server": [
            "rsync", "sysstat", "xz-utils"],
        "I@elasticsearch:server": [
            "python-elasticsearch"],
        # PROD-30833
        "I@octavia:manager:controller_worker:loadbalancer_topology:SINGLE": [
            "netfilter-persistent",
            "gunicorn",
            "octavia-worker",
            "octavia-health-manager",
            "octavia-housekeeping"]
        }
    exclude_packages = utils.get_configuration().get("skipped_packages", [])

    group_name, nodes = nodes_in_group
    packages_versions_by_nodes = salt.cmd(tgt="L@"+','.join(nodes),
                                              fun='lowpkg.list_pkgs',
                                              expr_form='compound')
    # Let's exclude cid01 and dbs01 nodes from this check
    exclude_nodes = targeted_minions("I@galera:master or I@gerrit:client")

    total_nodes = [i
                   for i in nodes
                   if i not in exclude_nodes]
    if len(total_nodes) < 2:
        pytest.skip("Nothing to compare - only 1 node")

    packages_with_different_versions = dict()
    packages_names = set(itertools.chain.from_iterable(
        [packages_versions_by_nodes[node].keys()
         for node in total_nodes])
    )

    for deb in packages_names:
        if deb in exclude_packages:
            continue

        node_and_version = [
            (node, packages_versions_by_nodes[node].get(deb, "No package"))
            for node in total_nodes
            if not is_deb_in_exception(inconsistency_rule, deb, node)
        ]

        if set([version for node, version in node_and_version]).__len__() > 1:
            packages_with_different_versions[deb] = [
                f"{node}: {version}"
                for node, version in node_and_version]

    assert len(packages_with_different_versions) == 0, (
        "Non-uniform package versions are installed on '{}' group of nodes:\n"
        "{}".format(
            group_name, json.dumps(packages_with_different_versions, indent=4))
    )


@pytest.mark.full
def test_packages_are_latest(local_salt_client, nodes_in_group):
    config = utils.get_configuration()
    skip = config.get("test_packages")["skip_test"]
    if skip.lower() == 'true':
        pytest.skip("Test for the latest packages is disabled")
    skipped_pkg = config.get("test_packages")["skipped_packages"]
    group, nodes = nodes_in_group
    info_salt = local_salt_client.cmd(
        tgt='L@' + ','.join(nodes),
        param='apt list --upgradable 2>/dev/null | grep -v Listing',
        expr_form='compound')
    for node in nodes:
        result = []
        if info_salt[node]:
            upg_list = info_salt[node].split('\n')
            for i in upg_list:
                if i.split('/')[0] not in skipped_pkg:
                    result.append(i)
        assert not result, (
            "Packages are not of latest version on '{}' node:\n{}".format(
                node, "\n".join(result))
        )


@pytest.mark.full
def test_check_module_versions(local_salt_client, nodes_in_group):
    # defines modules specific to the concrete nodes
    inconsistency_rule = {"I@elasticsearch:server": ["elasticsearch"]}
    exclude_modules = utils.get_configuration().get("skipped_modules", [])
    group, nodes = nodes_in_group
    pre_check = local_salt_client.cmd(
        tgt="L@"+','.join(nodes),
        param='dpkg -l | grep "python-pip "',
        expr_form='compound')
    if list(pre_check.values()).count('') > 0:
        pytest.skip("pip is not installed on one or more nodes")

    exclude_nodes = targeted_minions("I@galera:master or I@gerrit:client")

    # PROD-30833
    gtw01 = local_salt_client.pillar_get(
        param='_param:openstack_gateway_node01_hostname') or 'gtw01'
    cluster_domain = local_salt_client.pillar_get(
        param='_param:cluster_domain') or '.local'
    gtw01 += '.' + cluster_domain
    if gtw01 in nodes:
        octavia = local_salt_client.cmd(tgt="L@" + ','.join(nodes),
                                        fun='pillar.get',
                                        param='octavia:manager:enabled',
                                        expr_form='compound')
        gtws = [gtw for gtw in list(octavia.values()) if gtw]
        if len(gtws) == 1:
            exclude_nodes.append(gtw01)
            logging.info("gtw01 node is skipped in test_check_module_versions")

    total_nodes = [i for i in list(pre_check.keys()) if i not in exclude_nodes]

    if len(total_nodes) < 2:
        pytest.skip("Nothing to compare - only 1 node")
    list_of_pip_packages = local_salt_client.cmd(
        tgt="L@"+','.join(nodes),
        fun='pip.freeze', expr_form='compound')

    nodes_with_packages = []

    modules_with_different_versions = []
    packages_names = set()

    for node in total_nodes:
        nodes_with_packages.append(node)
        packages_names.update([x.split("=")[0] for x in list_of_pip_packages[node]])
        list_of_pip_packages[node] = dict([x.split("==") for x in list_of_pip_packages[node]])

    for deb in packages_names:
        if deb in exclude_modules:
            continue
        diff = []
        row = []
        for node in nodes_with_packages:
            if deb in list(list_of_pip_packages[node].keys()):
                diff.append(list_of_pip_packages[node][deb])
                row.append("{}: {}".format(node, list_of_pip_packages[node][deb]))
            else:
                row.append("{}: No module".format(node))
        if diff.count(diff[0]) < len(nodes_with_packages):
            if not is_deb_in_exception(inconsistency_rule, deb, row):
                row.sort()
                row.insert(0, deb)
                modules_with_different_versions.append(row)
    assert len(modules_with_different_versions) == 0, (
        "Non-uniform pip modules are installed on '{}' group of nodes:\n"
        "{}".format(
            group, json.dumps(modules_with_different_versions, indent=4))
    )


@pytest.mark.full
def test_restricted_updates_repo(local_salt_client):
    restricted_repo_enabled = local_salt_client.pillar_get(
        tgt="I@salt:master",
        param='_param:updates_mirantis_login',
        expr_form='compound')
    if not restricted_repo_enabled:
        pytest.skip("This env doesn't require the restricted ubuntu repo")

    repos_by_nodes=local_salt_client.cmd(
        tgt="*",
        param="apt-cache policy |grep updates.mirantis.com"
        )

    assert all(list(repos_by_nodes.values())), \
        "Next nodes don't have updates.mirantis.com in sources.list: {}".\
            format({node for node, repo
                   in repos_by_nodes.items()
                   if not repo})