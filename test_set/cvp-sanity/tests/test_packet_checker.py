import pytest
import json

import utils


def test_check_package_versions(local_salt_client, nodes_in_group):
    output = local_salt_client.cmd("L@"+','.join(nodes_in_group),
                                   'lowpkg.list_pkgs',
                                   expr_form='compound')
    # Let's exclude cid01 and dbs01 nodes from this check
    exclude_nodes = local_salt_client.cmd("I@galera:master or I@gerrit:client",
                                          'test.ping',
                                          expr_form='compound').keys()
    total_nodes = [i for i in output.keys() if i not in exclude_nodes]
    if len(total_nodes) < 2:
        pytest.skip("Nothing to compare - only 1 node")

    nodes = []
    pkts_data = []
    my_set = set()

    for node in total_nodes:
        nodes.append(node)
        my_set.update(output[node].keys())

    for deb in my_set:
        diff = []
        row = []
        for node in nodes:
            if deb in output[node].keys():
                diff.append(output[node][deb])
                row.append("{}: {}".format(node, output[node][deb]))
            else:
                row.append("{}: No package".format(node))
        if diff.count(diff[0]) < len(nodes):
            row.sort()
            row.insert(0, deb)
            pkts_data.append(row)
    assert len(pkts_data) <= 1, \
        "Several problems found: {0}".format(
        json.dumps(pkts_data, indent=4))


def test_packages_are_latest(local_salt_client, nodes_in_group):
    config = utils.get_configuration()
    skip = config.get("test_packages")["skip_test"]
    if skip:
        pytest.skip("Test for the latest packages is disabled")
    skipped_pkg = config.get("test_packages")["skipped_packages"]
    info_salt = local_salt_client.cmd(
        'L@' + ','.join(nodes_in_group),
        'cmd.run', ['apt list --upgradable 2>/dev/null | grep -v Listing'],
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


def test_check_module_versions(local_salt_client, nodes_in_group):
    pre_check = local_salt_client.cmd(
        "L@"+','.join(nodes_in_group),
        'cmd.run',
        ['dpkg -l | grep "python-pip "'],
        expr_form='compound')
    if pre_check.values().count('') > 0:
        pytest.skip("pip is not installed on one or more nodes")

    exclude_nodes = local_salt_client.cmd("I@galera:master or I@gerrit:client",
                                          'test.ping',
                                          expr_form='compound').keys()
    total_nodes = [i for i in pre_check.keys() if i not in exclude_nodes]

    if len(total_nodes) < 2:
        pytest.skip("Nothing to compare - only 1 node")
    output = local_salt_client.cmd("L@"+','.join(nodes_in_group),
                                   'pip.freeze', expr_form='compound')

    nodes = []

    pkts_data = []
    my_set = set()

    for node in total_nodes:
        nodes.append(node)
        my_set.update([x.split("=")[0] for x in output[node]])
        output[node] = dict([x.split("==") for x in output[node]])

    for deb in my_set:
        diff = []
        row = []
        for node in nodes:
            if deb in output[node].keys():
                diff.append(output[node][deb])
                row.append("{}: {}".format(node, output[node][deb]))
            else:
                row.append("{}: No module".format(node))
        if diff.count(diff[0]) < len(nodes):
            row.sort()
            row.insert(0, deb)
            pkts_data.append(row)
    assert len(pkts_data) <= 1, \
        "Several problems found: {0}".format(
        json.dumps(pkts_data, indent=4))
