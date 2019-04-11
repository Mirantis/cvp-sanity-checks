import os
import yaml
import requests
import re
import sys, traceback
import time


class AuthenticationError(Exception):
    pass


class salt_remote:
    def __init__(self):
        self.config = get_configuration()
        self.skipped_nodes = self.config.get('skipped_nodes') or []
        self.url = self.config['SALT_URL'].strip()
        if not re.match("^(http|https)://", self.url):
            raise AuthenticationError("Salt URL should start \
            with http or https, given - {}".format(url))
        self.login_payload = {'username': self.config['SALT_USERNAME'],
                              'password': self.config['SALT_PASSWORD'], 'eauth': 'pam'}
        # TODO: proxies
        self.proxies = {"http": None, "https": None}
        self.expires = ''
        self.cookies = []
        self.headers = {'Accept': 'application/json'}
        self._login()

    def _login (self):
        try:
            login_request = requests.post(os.path.join(self.url, 'login'),
                                          headers={'Accept': 'application/json'},
                                          data=self.login_payload,
                                          proxies=self.proxies)
            if not login_request.ok:
                raise AuthenticationError("Authentication to SaltMaster failed")
        except Exception as e:
            print ("\033[91m\nConnection to SaltMaster "
                  "was not established.\n"
                  "Please make sure that you "
                  "provided correct credentials.\n"
                  "Error message: {}\033[0m\n".format(e.message or e))
            traceback.print_exc(file=sys.stdout)
            sys.exit()
        self.expire = login_request.json()['return'][0]['expire']
        self.cookies = login_request.cookies
        self.headers['X-Auth-Token'] = login_request.json()['return'][0]['token']

    def cmd(self, tgt, fun='cmd.run', param=None, expr_form=None, tgt_type=None, check_status=False, retries=3):
        if self.expire < time.time() + 300:
            self.headers['X-Auth-Token'] = self._login()
        accept_key_payload = {'fun': fun, 'tgt': tgt, 'client': 'local',
                              'expr_form': expr_form, 'tgt_type': tgt_type,
                              'timeout': self.config['salt_timeout']}
        if param:
            accept_key_payload['arg'] = param

        for i in range(retries):
            request = requests.post(self.url, headers=self.headers,
                                    data=accept_key_payload,
                                    cookies=self.cookies,
                                    proxies=self.proxies)
            if not request.ok or not isinstance(request.json()['return'][0], dict):
                print("Salt master is not responding or response is incorrect. Output: {}".format(request))
                continue
            response = request.json()['return'][0]
            result = {key: response[key] for key in response if key not in self.skipped_nodes}
            if check_status:
                if False in result.values():
                    print(
                         "One or several nodes are not responding. Output {}".format(json.dumps(result, indent=4)))
                    continue
            break
        else:
            raise Exception("Error with Salt Master response")
        return result

    def test_ping(self, tgt, expr_form='pillar'):
        return self.cmd(tgt=tgt, fun='test.ping', param=None, expr_form=expr_form)

    def cmd_any(self, tgt, param=None, expr_form='pillar'):
        """
        This method returns first non-empty result on node or nodes.
        If all nodes returns nothing, then exception is thrown.
        """
        response = self.cmd(tgt=tgt, param=param, expr_form=expr_form)
        for node in response.keys():
            if response[node] or response[node] == '':
                return response[node]
        else:
            raise Exception("All minions are down")

    def pillar_get(self, tgt='salt:master', param=None, expr_form='pillar', fail_if_empty=False):
        """
        This method is for fetching pillars only.
        Returns value for pillar, False (if no such pillar) or if fail_if_empty=True - exception
        """
        response = self.cmd(tgt=tgt, fun='pillar.get', param=param, expr_form=expr_form)
        for node in response.keys():
            if response[node] or response[node] != '':
                return response[node]
        else:
            if fail_if_empty:
                raise Exception("No pillar found or it is empty.")
            else:
                return False


def init_salt_client():
    local = salt_remote()
    return local


def list_to_target_string(node_list, separator, add_spaces=True):
    if add_spaces:
        separator = ' ' + separator.strip() + ' '
    return separator.join(node_list)


def calculate_groups():
    config = get_configuration()
    local_salt_client = init_salt_client()
    node_groups = {}
    nodes_names = set ()
    expr_form = ''
    all_nodes = set(local_salt_client.test_ping(tgt='*',expr_form=None))
    print all_nodes
    if 'groups' in config.keys() and 'PB_GROUPS' in os.environ.keys() and \
       os.environ['PB_GROUPS'].lower() != 'false':
        nodes_names.update(config['groups'].keys())
        expr_form = 'compound'
    else:
        for node in all_nodes:
            index = re.search('[0-9]{1,3}$', node.split('.')[0])
            if index:
                nodes_names.add(node.split('.')[0][:-len(index.group(0))])
            else:
                nodes_names.add(node)
        expr_form = 'pcre'

    gluster_nodes = local_salt_client.test_ping(tgt='I@salt:control and '
                                          'I@glusterfs:server',
                                           expr_form='compound')
    kvm_nodes = local_salt_client.test_ping(tgt='I@salt:control and not '
                                      'I@glusterfs:server',
                                       expr_form='compound')

    for node_name in nodes_names:
        skipped_groups = config.get('skipped_groups') or []
        if node_name in skipped_groups:
            continue
        if expr_form == 'pcre':
            nodes = local_salt_client.test_ping(tgt='{}[0-9]{{1,3}}'.format(node_name),
                                                 expr_form=expr_form)
        else:
            nodes = local_salt_client.test_ping(tgt=config['groups'][node_name],
                                                 expr_form=expr_form)
            if nodes == {}:
                continue

        node_groups[node_name]=[x for x in nodes
                                if x not in config['skipped_nodes']
                                if x not in gluster_nodes.keys()
                                if x not in kvm_nodes.keys()]
        all_nodes = set(all_nodes - set(node_groups[node_name]))
        if node_groups[node_name] == []:
            del node_groups[node_name]
            if kvm_nodes:
                node_groups['kvm'] = kvm_nodes.keys()
            node_groups['kvm_gluster'] = gluster_nodes.keys()
    all_nodes = set(all_nodes - set(kvm_nodes.keys()))
    all_nodes = set(all_nodes - set(gluster_nodes.keys()))
    if all_nodes:
        print ("These nodes were not collected {0}. Check config (groups section)".format(all_nodes))
    return node_groups
                
            
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
