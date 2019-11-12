import json
import pytest
import logging


@pytest.mark.full
def test_uncommited_changes(local_salt_client):
    git_status = local_salt_client.cmd(
        tgt='salt:master',
        param='cd /srv/salt/reclass/classes/cluster/; git status',
        expr_form='pillar', check_status=True)
    assert 'nothing to commit' in list(git_status.values())[0], (
        "Git status shows some unmerged changes:\n{}".format(
            list(git_status.values())[0])
    )


@pytest.mark.smoke
def test_reclass_smoke(local_salt_client):
    reclass = local_salt_client.cmd(
        tgt='salt:master',
        param='reclass-salt --top; echo $?',
        expr_form='pillar', check_status=True)
    result = reclass[list(reclass.keys())[0]][-1]

    assert result == '0', 'Reclass is broken:\n{}'.format(reclass)


@pytest.mark.smoke
def test_reclass_nodes(local_salt_client):
    reclass = local_salt_client.cmd(
        tgt='salt:master',
        param='reclass-salt -o json --top',
        expr_form='pillar', check_status=True)
    salt = list(local_salt_client.cmd(
        tgt='salt:master',
        param='salt-run manage.status timeout=10 --out=json',
        expr_form='pillar', check_status=True).values())[0] or {}
    reclass_warnings = reclass[list(reclass.keys())[0]].split('{\n  "base":')[0]
    if reclass_warnings:
        logging.warning("\nReclass-salt output has warnings: {}".format(reclass_warnings))
    reclass_nodes = reclass[list(reclass.keys())[0]].split('{\n  "base":')[1]
    assert reclass_nodes != '', 'No nodes were found in' \
                                ' reclass-salt --top output'
    reclass_nodes = sorted(json.loads(reclass_nodes.strip("}")).keys())
    salt_nodes = sorted([x for xs in list(json.loads(salt).values()) for x in xs])
    assert salt_nodes == reclass_nodes, (
        "Mismatch between registered salt nodes (left) and node defined in "
        "reclass (right)."
    )
