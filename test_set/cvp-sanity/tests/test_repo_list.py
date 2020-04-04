import pytest
import logging
import json


@pytest.mark.full
def test_list_of_repo_on_nodes(local_salt_client, nodes_in_group):
    # TODO: pillar.get
    group, nodes = nodes_in_group
    info_salt = local_salt_client.cmd(tgt='L@' + ','.join(nodes),
                                      fun='pillar.get',
                                      param='linux:system:repo',
                                      expr_form='compound')

    secure_info = local_salt_client.cmd(
        tgt='L@' + ','.join(nodes), fun='pillar.get',
        param='linux:system:common_repo_secured', expr_form='compound')

    secured_repos, username, password = ([], None, None)

    if isinstance(secure_info, dict) and len(secure_info) > 0:
        info_tmp = secure_info.popitem()[1]
        if isinstance(info_tmp, dict):
            secured_repos, username, password = (info_tmp.get(key, [])
                for key in ['secured_repos', 'user', 'password'])

    # check if some repos are disabled
    for node in list(info_salt.keys()):
        repos = info_salt[node]
        if not info_salt[node]:
            # TODO: do not skip node
            logging.warning("Node {} is skipped".format(node))
            continue
        for repo in list(repos.keys()):
            repository = repos[repo]
            if "enabled" in repository:
                if not repository["enabled"]:
                    repos.pop(repo)
            if repo in secured_repos or ('all' in secured_repos and
                                         repos[repo].get('secure', True)):
                repos[repo]['source'] = repos[repo]['source'].replace(
                    '://', '://{}:{}@'.format(username, password))

    raw_actual_info = local_salt_client.cmd(
        tgt='L@' + ','.join(nodes),
        param='cat /etc/apt/sources.list.d/*;'
              'cat /etc/apt/sources.list|grep deb|grep -v "#"',
        expr_form='compound', check_status=True)
    actual_repo_list = [
        item.replace('/ ', ' ').replace('[arch=amd64] ', '')
        for item in list(raw_actual_info.values())[0].split('\n')
    ]
    if list(info_salt.values())[0] == '':
        expected_salt_data = ''
    else:
        expected_salt_data = [repo['source'].replace('/ ', ' ')
                                            .replace('[arch=amd64] ', '')
                              for repo in list(info_salt.values())[0].values()
                              if 'source' in list(repo.keys())]

    diff = {}
    my_set = set()
    fail_counter = 0
    my_set.update(actual_repo_list)
    my_set.update(expected_salt_data)
    for repo in my_set:
        rows = []
        if repo not in actual_repo_list:
            rows.append("{}: {}".format("pillars", "+"))
            rows.append("{}: No repo".format('config'))
            diff[repo] = rows
            fail_counter += 1
        elif repo not in expected_salt_data:
            rows.append("{}: {}".format("config", "+"))
            rows.append("{}: No repo".format('pillars'))
            diff[repo] = rows
    assert fail_counter == 0, (
        "Non-uniform repos are on '{}' group of nodes:\n{}".format(
            group, json.dumps(diff, indent=4))
    )
    if fail_counter == 0 and len(diff) > 0:
        logging.warning("\nWarning: nodes contain more repos than reclass")
