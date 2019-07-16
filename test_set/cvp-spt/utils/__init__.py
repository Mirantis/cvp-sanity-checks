import os
import yaml
import requests
import re
import sys, traceback
import itertools
import helpers
from utils import os_client


class salt_remote:
    def cmd(self, tgt, fun, param=None, expr_form=None, tgt_type=None):
        config = get_configuration()
        url = config['SALT_URL']
        proxies = {"http": None, "https": None}
        headers = {'Accept': 'application/json'}
        login_payload = {'username': config['SALT_USERNAME'],
                         'password': config['SALT_PASSWORD'], 'eauth': 'pam'}
        accept_key_payload = {'fun': fun, 'tgt': tgt, 'client': 'local',
                              'expr_form': expr_form, 'tgt_type': tgt_type,
                              'timeout': config['salt_timeout']}
        if param:
            accept_key_payload['arg'] = param

        try:
            login_request = requests.post(os.path.join(url, 'login'),
                                          headers=headers, data=login_payload,
                                          proxies=proxies)
            if login_request.ok:
                request = requests.post(url, headers=headers,
                                        data=accept_key_payload,
                                        cookies=login_request.cookies,
                                        proxies=proxies)
                return request.json()['return'][0]
        except Exception:
            print "\033[91m\nConnection to SaltMaster " \
                  "was not established.\n" \
                  "Please make sure that you " \
                  "provided correct credentials.\033[0m\n"
            traceback.print_exc(file=sys.stdout)
            sys.exit()


def init_salt_client():
    local = salt_remote()
    return local


def compile_pairs (nodes):
    result = {}
    if len(nodes) %2 != 0:
        nodes.pop(1)
    pairs = zip(*[iter(nodes)]*2)
    for pair in pairs:
        result[pair[0]+'<>'+pair[1]] = pair
    return result


def get_pairs():
    # TODO
    # maybe collect cmp from nova service-list
    config = get_configuration()
    local_salt_client = init_salt_client()
    cmp_hosts = config.get('CMP_HOSTS') or []
    skipped_nodes = config.get('skipped_nodes') or []
    if skipped_nodes:
        print "Notice: {0} nodes will be skipped for vm2vm test".format(skipped_nodes)
    if not cmp_hosts:
        nodes = local_salt_client.cmd(
                'I@nova:compute',
                'test.ping',
                expr_form='compound')
        cmp_hosts = [node.split('.')[0] for node in nodes.keys() if node not in skipped_nodes]
    return compile_pairs(cmp_hosts)


def get_hw_pairs():
    config = get_configuration()
    local_salt_client = init_salt_client()
    hw_nodes = config.get('HW_NODES') or []
    skipped_nodes = config.get('skipped_nodes') or []
    if skipped_nodes:
        print "Notice: {0} nodes will be skipped for hw2hw test".format(skipped_nodes)
    if not hw_nodes:
        nodes = local_salt_client.cmd(
                'I@salt:control or I@nova:compute',
                'test.ping',
                expr_form='compound')
        hw_nodes = [node for node in nodes.keys() if node not in skipped_nodes]
    print local_salt_client.cmd(expr_form='compound', tgt="L@"+','.join(hw_nodes),
                                fun='pkg.install', param=['iperf'])
    return compile_pairs(hw_nodes)

def get_configuration():
    """function returns configuration for environment
    and for test if it's specified"""

    global_config_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "../global_config.yaml")
    with open(global_config_file, 'r') as file:
        global_config = yaml.load(file, Loader=yaml.SafeLoader)
    for param in global_config.keys():
        if param in os.environ.keys():
            if ',' in os.environ[param]:
                global_config[param] = []
                for item in os.environ[param].split(','):
                    global_config[param].append(item)
            else:
                global_config[param] = os.environ[param]

    return global_config
