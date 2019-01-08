#!/usr/bin/env python
import itertools
import re
import os
import yaml
import requests
from cvp_spt import utils
from cvp_spt.utils import helpers
from netaddr import IPNetwork, IPAddress


def test_hw2hw (local_salt_client,hw_pair,record_property):
    helpp = helpers.helpers(local_salt_client)
    config = utils.get_configuration()
    nodes = local_salt_client.cmd(expr_form='compound', tgt=str(hw_pair[0]+' or '+hw_pair[1]),
                                  fun='network.interfaces')
    short_name = []
    short_name.append(hw_pair[0].split('.')[0])
    short_name.append(hw_pair[1].split('.')[0])
    nets = config.get('networks').split(',')
    local_salt_client.cmd(expr_form='compound', tgt=str(hw_pair[0]+' or '+hw_pair[1]),
                          fun='cmd.run', param=['nohup iperf -s > file 2>&1 &'])
    global_results = []
    for net in nets:
        for interf in nodes[hw_pair[0]]:
            if 'inet' not in nodes[hw_pair[0]][interf].keys():
                continue
            ip = nodes[hw_pair[0]][interf]['inet'][0]['address']
            if (IPAddress(ip) in IPNetwork(net)) and (nodes[hw_pair[0]][interf]['inet'][0]['broadcast']):
                for interf2 in nodes[hw_pair[1]]:
                    if 'inet' not in nodes[hw_pair[1]][interf2].keys():
                        continue
                    ip2 = nodes[hw_pair[1]][interf2]['inet'][0]['address']
                    if (IPAddress(ip2) in IPNetwork(net)) and (nodes[hw_pair[1]][interf2]['inet'][0]['broadcast']):
                        print "Will IPERF between {0} and {1}".format(ip,ip2)
                        try:
                            res = helpp.start_iperf_between_hosts(global_results, hw_pair[0], hw_pair[1],
                                                                      ip, ip2, net)
                            record_property("1-worst {0}-{1}".format(short_name[0],short_name[1]), res[0] if res[0] < res[2] else res[2])
                            record_property("1-best {0}-{1}".format(short_name[0],short_name[1]), res[0] if res[0] > res[2] else res[2])
                            record_property("10-best {0}-{1}".format(short_name[0],short_name[1]), res[1] if res[1] > res[3] else res[3])
                            record_property("10-best {0}-{1}".format(short_name[0],short_name[1]), res[1] if res[1] > res[3] else res[3])
                            print "Measurement between {} and {} " \
                                   "has been finished".format(hw_pair[0],
                                                              hw_pair[1])
                        except Exception as e:
                                print "Failed for {0} {1}".format(
                                              hw_pair[0], hw_pair[1])
                                print e
    local_salt_client.cmd(expr_form='compound', tgt=str(hw_pair[0]+' or '+hw_pair[1]),
                          fun='cmd.run', param=['killall -9 iperf'])
    helpp.draw_table_with_results(global_results)
