def test_uncommited_changes(local_salt_client):
    git_status = local_salt_client.cmd(
        'salt:master',
        'cmd.run',
        ['cd /srv/salt/reclass/classes/cluster/; git status'],
        expr_form='pillar')
    assert 'nothing to commit' in git_status.values()[0], 'Git status showed' \
           ' some unmerged changes {}'''.format(git_status.values()[0])


def test_reclass_smoke(local_salt_client):
    reclass = local_salt_client.cmd(
        'salt:master',
        'cmd.run',
        ['reclass-salt --top; echo $?'],
        expr_form='pillar')
    result = reclass[reclass.keys()[0]][-1]

    assert result == '0', 'Reclass is broken' \
                          '\n {}'.format(reclass)
