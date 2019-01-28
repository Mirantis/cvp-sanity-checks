import json
import requests
import datetime
import pytest
import utils


@pytest.mark.usefixtures('check_kibana')
def test_elasticsearch_cluster(local_salt_client):
    salt_output = local_salt_client.cmd(
        'kibana:server',
        'pillar.get',
        ['_param:haproxy_elasticsearch_bind_host'],
        expr_form='pillar')

    proxies = {"http": None, "https": None}
    for node in salt_output.keys():
        IP = salt_output[node]
        assert requests.get('http://{}:9200/'.format(IP),
                            proxies=proxies).status_code == 200, \
            'Cannot check elasticsearch url on {}.'.format(IP)
        resp = requests.get('http://{}:9200/_cat/health'.format(IP),
                            proxies=proxies).content
        assert resp.split()[3] == 'green', \
            'elasticsearch status is not good {}'.format(
            json.dumps(resp, indent=4))
        assert resp.split()[4] == '3', \
            'elasticsearch status is not good {}'.format(
            json.dumps(resp, indent=4))
        assert resp.split()[5] == '3', \
            'elasticsearch status is not good {}'.format(
            json.dumps(resp, indent=4))
        assert resp.split()[10] == '0', \
            'elasticsearch status is not good {}'.format(
            json.dumps(resp, indent=4))
        assert resp.split()[13] == '100.0%', \
            'elasticsearch status is not good {}'.format(
            json.dumps(resp, indent=4))


@pytest.mark.usefixtures('check_kibana')
def test_kibana_status(local_salt_client):
    proxies = {"http": None, "https": None}
    IP = utils.get_monitoring_ip('stacklight_log_address')
    resp = requests.get('http://{}:5601/api/status'.format(IP),
                        proxies=proxies).content
    body = json.loads(resp)
    assert body['status']['overall']['state'] == "green", \
        "Kibana status is not expected: {}".format(
        body['status']['overall'])
    for i in body['status']['statuses']:
        assert i['state'] == "green", \
            "Kibana statuses are unexpected: {}".format(i)


@pytest.mark.usefixtures('check_kibana')
def test_elasticsearch_node_count(local_salt_client):
    now = datetime.datetime.now()
    today = now.strftime("%Y.%m.%d")
    active_nodes = utils.get_active_nodes()
    salt_output = local_salt_client.cmd(
        'kibana:server',
        'pillar.get',
        ['_param:haproxy_elasticsearch_bind_host'],
        expr_form='pillar')

    IP = salt_output.values()[0]
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    proxies = {"http": None, "https": None}
    data = ('{"size": 0, "aggs": '
            '{"uniq_hostname": '
            '{"terms": {"size": 1000, '
            '"field": "Hostname.keyword"}}}}')
    response = requests.post(
        'http://{0}:9200/log-{1}/_search?pretty'.format(IP, today),
        proxies=proxies,
        headers=headers,
        data=data)
    assert 200 == response.status_code, 'Unexpected code {}'.format(
        response.text)
    resp = json.loads(response.text)
    cluster_domain = local_salt_client.cmd('salt:control',
                                           'pillar.get',
                                           ['_param:cluster_domain'],
                                           expr_form='pillar').values()[0]
    monitored_nodes = []
    for item_ in resp['aggregations']['uniq_hostname']['buckets']:
        node_name = item_['key']
        monitored_nodes.append(node_name + '.' + cluster_domain)
    missing_nodes = []
    for node in active_nodes.keys():
        if node not in monitored_nodes:
            missing_nodes.append(node)
    assert len(missing_nodes) == 0, \
        'Not all nodes are in Elasticsearch. Found {0} keys, ' \
        'expected {1}. Missing nodes: \n{2}'. \
            format(len(monitored_nodes), len(active_nodes), missing_nodes)


def test_stacklight_services_replicas(local_salt_client):
    # TODO
    # change to docker:swarm:role:master ?
    salt_output = local_salt_client.cmd(
        'I@docker:client:stack:monitoring and I@prometheus:server',
        'cmd.run',
        ['docker service ls'],
        expr_form='compound')

    if not salt_output:
        pytest.skip("docker:client:stack:monitoring or \
        prometheus:server pillars are not found on this environment.")

    wrong_items = []
    for line in salt_output[salt_output.keys()[0]].split('\n'):
        if line[line.find('/') - 1] != line[line.find('/') + 1] \
           and 'replicated' in line:
            wrong_items.append(line)
    assert len(wrong_items) == 0, \
        '''Some monitoring services doesn't have expected number of replicas:
              {}'''.format(json.dumps(wrong_items, indent=4))


@pytest.mark.usefixtures('check_prometheus')
def test_prometheus_alert_count(local_salt_client):
    IP = utils.get_monitoring_ip('cluster_public_host')
    # keystone:server can return 3 nodes instead of 1
    # this will be fixed later
    # TODO
    nodes_info = local_salt_client.cmd(
        'keystone:server',
        'cmd.run',
        ['curl -s http://{}:15010/alerts | grep icon-chevron-down | '
         'grep -v "0 active"'.format(IP)],
        expr_form='pillar')

    result = nodes_info[nodes_info.keys()[0]].replace('</td>', '').replace(
        '<td><i class="icon-chevron-down"></i> <b>', '').replace('</b>', '')
    assert result == '', 'AlertManager page has some alerts! {}'.format(
                         json.dumps(result), indent=4)


def test_stacklight_containers_status(local_salt_client):
    salt_output = local_salt_client.cmd(
        'I@docker:swarm:role:master and I@prometheus:server',
        'cmd.run',
        ['docker service ps $(docker stack services -q monitoring)'],
        expr_form='compound')

    if not salt_output:
        pytest.skip("docker:swarm:role:master or prometheus:server \
        pillars are not found on this environment.")

    result = {}
    # for old reclass models, docker:swarm:role:master can return
    # 2 nodes instead of one. Here is temporary fix.
    # TODO
    if len(salt_output.keys()) > 1:
        if 'CURRENT STATE' not in salt_output[salt_output.keys()[0]]:
            del salt_output[salt_output.keys()[0]]
    for line in salt_output[salt_output.keys()[0]].split('\n')[1:]:
        shift = 0
        if line.split()[1] == '\\_':
            shift = 1
        if line.split()[1 + shift] not in result.keys():
            result[line.split()[1]] = 'NOT OK'
        if line.split()[4 + shift] == 'Running' \
           or line.split()[4 + shift] == 'Ready':
            result[line.split()[1 + shift]] = 'OK'
    assert 'NOT OK' not in result.values(), \
        '''Some containers are in incorrect state:
              {}'''.format(json.dumps(result, indent=4))


def test_running_telegraf_services(local_salt_client):
    salt_output = local_salt_client.cmd('telegraf:agent',
                                        'service.status',
                                        'telegraf',
                                        expr_form='pillar')

    if not salt_output:
        pytest.skip("Telegraf or telegraf:agent \
        pillar are not found on this environment.")

    result = [{node: status} for node, status
              in salt_output.items()
              if status is False]
    assert result == [], 'Telegraf service is not running ' \
                         'on following nodes: {}'.format(result)


def test_running_fluentd_services(local_salt_client):
    salt_output = local_salt_client.cmd('fluentd:agent',
                                        'service.status',
                                        'td-agent',
                                        expr_form='pillar')
    result = [{node: status} for node, status
              in salt_output.items()
              if status is False]
    assert result == [], 'Fluentd check failed: td-agent service is not ' \
                         'running on following nodes:'.format(result)
