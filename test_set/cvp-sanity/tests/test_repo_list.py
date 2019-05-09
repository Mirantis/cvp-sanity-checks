import pytest


@pytest.mark.full
def test_list_of_repo_on_nodes(local_salt_client, nodes_in_group):
    # TODO: pillar.get
    info_salt = local_salt_client.cmd(tgt='L@' + ','.join(
                                              nodes_in_group),
                                      fun='pillar.get',
                                      param='linux:system:repo',
                                      expr_form='compound')

    # check if some repos are disabled
    for node in info_salt.keys():
        repos = info_salt[node]
        if not info_salt[node]:
            # TODO: do not skip node
            print "Node {} is skipped".format (node)
            continue
        for repo in repos.keys():
            repository = repos[repo]
            if "enabled" in repository:
                if not repository["enabled"]:
                    repos.pop(repo)

    raw_actual_info = local_salt_client.cmd(
        tgt='L@' + ','.join(
            nodes_in_group),
        param='cat /etc/apt/sources.list.d/*;'
              'cat /etc/apt/sources.list|grep deb|grep -v "#"',
        expr_form='compound', check_status=True)
    actual_repo_list = [item.replace('/ ', ' ').replace('[arch=amd64] ', '')
                        for item in raw_actual_info.values()[0].split('\n')]
    if info_salt.values()[0] == '':
        expected_salt_data = ''
    else:
        expected_salt_data = [repo['source'].replace('/ ', ' ')
                                            .replace('[arch=amd64] ', '')
                              for repo in info_salt.values()[0].values()
                              if 'source' in repo.keys()]

    diff = {}
    my_set = set()
    fail_counter = 0
    my_set.update(actual_repo_list)
    my_set.update(expected_salt_data)
    import json
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
    assert fail_counter == 0, \
        "Several problems found: {0}".format(
            json.dumps(diff, indent=4))
    if fail_counter == 0 and len(diff) > 0:
        print "\nWarning: nodes contain more repos than reclass"
