import pytest
import json
import os
import utils


def test_etc_hosts(local_salt_client):
    active_nodes = utils.get_active_nodes()
    nodes_info = local_salt_client.cmd(
        utils.list_to_target_string(active_nodes, 'or'), 'cmd.run',
        ['cat /etc/hosts'],
        expr_form='compound')
    result = {}
    for node in nodes_info.keys():
        for nd in nodes_info.keys():
           if node not in nodes_info[nd]:
              if node in result:
                  result[node]+=','+nd
              else:
                  result[node]=nd
    assert len(result) <= 1, \
        "Some hosts are not presented in /etc/hosts: {0}".format(
         json.dumps(result, indent=4))     
