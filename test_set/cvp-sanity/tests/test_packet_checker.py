import pytest
import json
import utils
import logging

def is_deb_in_exception(package_name, error_node_list):
    # defines packages specific to the concrete nodes
    inconsistency_rule = {"kvm03": ["rsync", "sysstat", "xz-utils"], "log01": ["python-elasticsearch"]}
    short_names_in_error_nodes = [n.split('.')[0] for n in error_node_list]
    for node, excluded_packages in inconsistency_rule.iteritems():
        if package_name in excluded_packages and node in short_names_in_error_nodes:
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
        If pachage name in the eception list or in inconsistency_rule, ignore it.
     4) Compare items in that list - they should be equal and match the amout of nodes

    """
    exclude_packages = utils.get_configuration().get("skipped_packages", [])
    packages_versions = local_salt_client.cmd(tgt="L@"+','.join(nodes_in_group),
                                              fun='lowpkg.list_pkgs',
                                              expr_form='compound')
    # Let's exclude cid01 and dbs01 nodes from this check
    exclude_nodes = local_salt_client.test_ping(tgt="I@galera:master or I@gerrit:client",
                                                expr_form='compound').keys()
    # PROD-30833
    gtw01 = local_salt_client.pillar_get(
        param='_param:openstack_gateway_node01_hostname') or 'gtw01'
    cluster_domain = local_salt_client.pillar_get(
        param='_param:cluster_domain') or '.local'
    gtw01 += '.' + cluster_domain
    if gtw01 in nodes_in_group:
        octavia = local_salt_client.cmd(tgt="L@" + ','.join(nodes_in_group),
                                        fun='pillar.get',
                                        param='octavia:manager:enabled',
                                        expr_form='compound')
        gtws = [gtw for gtw in octavia.values() if gtw]
        if len(gtws) == 1:
            exclude_nodes.append(gtw01)
            logging.info("gtw01 node is skipped in test_check_package_versions")

    total_nodes = [i for i in nodes_in_group if i not in exclude_nodes]
    if len(total_nodes) < 2:
        pytest.skip("Nothing to compare - only 1 node")
    nodes_with_packages = []
    packages_with_different_versions = []
    packages_names = set()

    for node in total_nodes:
        if not packages_versions[node]:
            # TODO: do not skip node
            logging.warning("Node {} is skipped".format(node))
            continue
        nodes_with_packages.append(node)
        packages_names.update(packages_versions[node].keys())
    for deb in packages_names:
        if deb in exclude_packages:
            continue
        diff = []
        row = []
        for node in nodes_with_packages:
            if not packages_versions[node]:
                continue
            if deb in packages_versions[node].keys():
                diff.append(packages_versions[node][deb])
                row.append("{}: {}".format(node, packages_versions[node][deb]))
            else:
                row.append("{}: No package".format(node))

        if diff.count(diff[0]) < len(nodes_with_packages):
           if not is_deb_in_exception(deb, row):
                row.sort()
                row.insert(0, deb)
                packages_with_different_versions.append(row)
    assert len(packages_with_different_versions) == 0, \
        "Several problems found: {0}".format(
        json.dumps(packages_with_different_versions, indent=4))


@pytest.mark.full
def test_packages_are_latest(local_salt_client, nodes_in_group):
    config = utils.get_configuration()
    skip = config.get("test_packages")["skip_test"]
    if skip:
        pytest.skip("Test for the latest packages is disabled")
    skipped_pkg = config.get("test_packages")["skipped_packages"]
    info_salt = local_salt_client.cmd(
        tgt='L@' + ','.join(nodes_in_group),
        param='apt list --upgradable 2>/dev/null | grep -v Listing',
        expr_form='compound')
    for node in nodes_in_group:
        result = []
        if info_salt[node]:
            upg_list = info_salt[node].split('\n')
            for i in upg_list:
                if i.split('/')[0] not in skipped_pkg:
                    result.append(i)
        assert not result, "Please check not latest packages at {}:\n{}".format(
            node, "\n".join(result))


@pytest.mark.full
def test_check_module_versions(local_salt_client, nodes_in_group):
    exclude_modules = utils.get_configuration().get("skipped_modules", [])
    pre_check = local_salt_client.cmd(
        tgt="L@"+','.join(nodes_in_group),
        param='dpkg -l | grep "python-pip "',
        expr_form='compound')
    if pre_check.values().count('') > 0:
        pytest.skip("pip is not installed on one or more nodes")

    exclude_nodes = local_salt_client.test_ping(tgt="I@galera:master or I@gerrit:client",
                                                expr_form='compound').keys()

    # PROD-30833
    gtw01 = local_salt_client.pillar_get(
        param='_param:openstack_gateway_node01_hostname') or 'gtw01'
    cluster_domain = local_salt_client.pillar_get(
        param='_param:cluster_domain') or '.local'
    gtw01 += '.' + cluster_domain
    if gtw01 in nodes_in_group:
        octavia = local_salt_client.cmd(tgt="L@" + ','.join(nodes_in_group),
                                        fun='pillar.get',
                                        param='octavia:manager:enabled',
                                        expr_form='compound')
        gtws = [gtw for gtw in octavia.values() if gtw]
        if len(gtws) == 1:
            exclude_nodes.append(gtw01)
            logging.info("gtw01 node is skipped in test_check_module_versions")

    total_nodes = [i for i in pre_check.keys() if i not in exclude_nodes]

    if len(total_nodes) < 2:
        pytest.skip("Nothing to compare - only 1 node")
    list_of_pip_packages = local_salt_client.cmd(tgt="L@"+','.join(nodes_in_group),
                                   fun='pip.freeze', expr_form='compound')

    nodes = []

    pkts_data = []
    packages_names = set()

    for node in total_nodes:
        nodes.append(node)
        packages_names.update([x.split("=")[0] for x in list_of_pip_packages[node]])
        list_of_pip_packages[node] = dict([x.split("==") for x in list_of_pip_packages[node]])

    for deb in packages_names:
        if deb in exclude_modules:
            continue
        diff = []
        row = []
        for node in nodes:
            if deb in list_of_pip_packages[node].keys():
                diff.append(list_of_pip_packages[node][deb])
                row.append("{}: {}".format(node, list_of_pip_packages[node][deb]))
            else:
                row.append("{}: No module".format(node))
        if diff.count(diff[0]) < len(nodes):
            row.sort()
            row.insert(0, deb)
            pkts_data.append(row)
    assert len(pkts_data) <= 1, \
        "Several problems found: {0}".format(
        json.dumps(pkts_data, indent=4))
