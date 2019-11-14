import copy
import json

import pytest


@pytest.mark.smoke
@pytest.mark.usefixtures('check_openstack')
def test_fernet_token_consistency(local_salt_client):
    """
    The test checks that /var/lib/keystone/fernet-keys/ directory at ctl*:
    * has the same files and same number of files;
    * all same files on different ctl* nodes have the same MD5 sum.

    When fernet token rotation is not equal on all ctl* nodes and these files
    are not consistent, the OpenStack API works unexpectedly and responds with
    random 500 HTTP errors for random requests.
    """
    fernet_keys_files = local_salt_client.cmd(
        tgt='keystone:server',
        param='ls -1 /var/lib/keystone/fernet-keys/',
        expr_form='pillar')
    for k in fernet_keys_files:
        fernet_keys_files[k] = fernet_keys_files[k].replace('\n', ', ')
    assert len(set(fernet_keys_files.values())) == 1, (
        "Fernet keys files are not equal on all nodes, please check "
        "/var/lib/keystone/fernet-keys/ at all ctl* nodes: {}".format(
            json.dumps(fernet_keys_files, indent=4)))

    md5sums = local_salt_client.cmd(
        tgt='keystone:server',
        param='md5sum /var/lib/keystone/fernet-keys/*',
        expr_form='pillar')
    md5sums_print = copy.deepcopy(md5sums)
    for k in md5sums_print: md5sums_print[k] = md5sums_print[k].split('\n')
    assert len(set(md5sums.values())) == 1, (
        "Fernet keys files are not consistent - MD5 sums are not equal on "
        "all ctl* nodes: {}".format(json.dumps(md5sums_print, indent=4)))
