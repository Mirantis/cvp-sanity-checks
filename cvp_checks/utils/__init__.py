import os
import yaml
import requests
import re


class salt_remote:
    def cmd(self, tgt, fun, param=None, expr_form=None, tgt_type=None):
        config = get_configuration()
        headers = {'Accept': 'application/json'}
        login_payload = {'username': config['SALT_USERNAME'],
                         'password': config['SALT_PASSWORD'], 'eauth': 'pam'}
        accept_key_payload = {'fun': fun, 'tgt': tgt, 'client': 'local',
                              'expr_form': expr_form, 'tgt_type': tgt_type}
        if param:
            accept_key_payload['arg'] = param

        login_request = requests.post(os.path.join(config['SALT_URL'],
                                                   'login'),
                                      headers=headers, data=login_payload)
        if login_request.ok:
            request = requests.post(config['SALT_URL'], headers=headers,
                                    data=accept_key_payload,
                                    cookies=login_request.cookies)
            return request.json()['return'][0]
        else:
            raise EnvironmentError("401 Not authorized.")


def init_salt_client():
    local = salt_remote()
    return local


def list_to_target_string(node_list, separator):
    result = ''
    for node in node_list:
        result += node + ' ' + separator + ' '
    return result.strip(' ' + separator + ' ')


def get_monitoring_ip(param_name):
    local_salt_client = init_salt_client()
    salt_output = local_salt_client.cmd(
        'docker:client:stack:monitoring',
        'pillar.get',
        ['_param:{}'.format(param_name)],
        expr_form='pillar')
    return salt_output[salt_output.keys()[0]]


def get_active_nodes(test=None):
    config = get_configuration()
    local_salt_client = init_salt_client()

    skipped_nodes = config.get('skipped_nodes') or []
    if test:
        testname = test.split('.')[0]
        if 'skipped_nodes' in config.get(testname).keys():
            skipped_nodes += config.get(testname)['skipped_nodes'] or []

    if skipped_nodes != ['']:
        print "\nNotice: {0} nodes will be skipped".format(skipped_nodes)
        nodes = local_salt_client.cmd(
            '* and not ' + list_to_target_string(skipped_nodes, 'and not'),
            'test.ping',
            expr_form='compound')
    else:
        nodes = local_salt_client.cmd('*', 'test.ping')
    return nodes


def get_groups(test):
    config = get_configuration()
    testname = test.split('.')[0]
    # assume that node name is like <name>.domain
    # last 1-3 digits of name are index, e.g. 001 in cpu001
    # name doesn't contain dots
    active_nodes = get_active_nodes()

    skipped_groups = config.get('skipped_groups') or []
    if config.get(testname):
        if 'skipped_groups' in config.get(testname).keys():
            skipped_groups += config.get(testname)['skipped_groups'] or []

    groups = []

    for node in active_nodes:
        index = re.search('[0-9]{1,3}$', node.split('.')[0])
        if index:
            group_name = node.split('.')[0][:-len(index.group(0))]
        else:
            group_name = node
        if group_name not in groups:
            if group_name not in skipped_groups:
                groups.append(group_name)
            else:
                if group_name + " - skipped" not in groups:
                    groups.append(group_name + " - skipped")

    return groups


def get_configuration():
    """function returns configuration for environment
    and for test if it's specified"""
    global_config_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "../global_config.yaml")
    with open(global_config_file, 'r') as file:
        global_config = yaml.load(file)
    for param in global_config.keys():
        if param in os.environ.keys():
            if ',' in os.environ[param]:
                global_config[param] = []
                for item in os.environ[param].split(','):
                    global_config[param].append(item)
            else:
                global_config[param] = os.environ[param]

    return global_config
