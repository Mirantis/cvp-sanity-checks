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
     4) Compare items in that list - they should be equal and match the
     amount of nodes

    """
    salt = local_salt_client
    # defines packages specific to the nodes
    inconsistency_rule = {
        "I@backupninja:server": [
            "rsync", "sysstat", "xz-utils"],
        "I@elasticsearch:server": [
            "python-elasticsearch"],
        # PROD-30833, PROD-36718
        "I@octavia:manager:controller_worker:loadbalancer_topology:SINGLE": [
            "netfilter-persistent",
            "gunicorn",
            "octavia-worker",
            "octavia-health-manager",
            "octavia-housekeeping",
            "python-castellan",
            'python-automaton',
            'python-setproctitle',
            'python-glanceclient',
            'libnss3-nssdb',
            'python-json-pointer',
            'debootstrap',
            'python-cotyledon',
            'librbd1',
            'qemu-block-extra:amd64',
            'python-diskimage-builder',
            'liburcu4:amd64',
            'python-networkx',
            'librados2',
            'kpartx',
            'python-taskflow',
            'libnss3:amd64',
            'libibverbs1',
            'python-itsdangerous',
            'liblttng-ust0:amd64',
            'python-wsme',
            'python-werkzeug',
            'liblttng-ust-ctl2:amd64',
            'python-gunicorn',
            'python-octavia',
            'python-warlock',
            'python-barbicanclient',
            'iptables-persistent',
            'python-psycopg2',
            'octavia-common',
            'python-flask',
            'libpq5:amd64',
            'python-dib-utils',
            'python-jsonpatch',
            'libnspr4:amd64',
            'qemu-utils',
            'python-pyasn1-modules',
            'libonig2:amd64',
            'jq',
            'libaio1:amd64',
            'python-kazoo',
            'python-ipaddr',
            'libiscsi2:amd64',
            'python-pyasn1',
            'python3-pyasn1'
        ]
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
                "{}: {}".format(node, version)
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
    # defines modules specific to the nodes
    inconsistency_rule = {
        "I@elasticsearch:server": ["elasticsearch"],
        # PROD-30833
        "I@octavia:manager:controller_worker:loadbalancer_topology:SINGLE": [
            'octavia',
            'setproctitle',
            'automaton',
            'warlock',
            'python-glanceclient',
            'taskflow',
            'diskimage-builder',
            'pyasn1-modules',
            'python-barbicanclient',
            'WSME',
            'jsonpatch',
            'cotyledon',
            'dib-utils',
            'itsdangerous',
            'kazoo',
            'psycopg2',
            'Flask',
            'networkx',
            'Werkzeug',
            'jsonpointer',
            'gunicorn',
            'ipaddr',
            'castellan'
        ]
    }
    exclude_modules = utils.get_configuration().get("skipped_modules", [])
    group, nodes = nodes_in_group

    pre_check = local_salt_client.cmd(
        tgt="L@{nodes}".format(nodes=','.join(nodes)),
        param='dpkg -l | grep "python-pip "',
        expr_form='compound')
    exclude_nodes = targeted_minions("I@galera:master or I@gerrit:client")
    if list(pre_check.values()).count('') > 0:
        pytest.skip("pip is not installed on one or more nodes")

    total_nodes = [node
                   for node in nodes
                   if node not in exclude_nodes]
    if len(total_nodes) < 2:
        pytest.skip("Nothing to compare - only 1 node")
    list_of_pip_packages = local_salt_client.cmd(
        tgt="L@"+','.join(nodes),
        fun='pip.list', expr_form='compound')

    modules_with_different_versions = dict()
    packages_names = set(itertools.chain.from_iterable(
        list_of_pip_packages.values()
    ))

    for package in packages_names:
        if package in exclude_modules:
            continue
        node_and_version = [
            (node, list_of_pip_packages[node].get(package, "No module"))
            for node in total_nodes
            if not is_deb_in_exception(inconsistency_rule, package, node)
        ]

        if set([version for node, version in node_and_version]).__len__() > 1:
            modules_with_different_versions[package] = [
                "{}: {}".format(node, version)
                for node, version in node_and_version
            ]

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
