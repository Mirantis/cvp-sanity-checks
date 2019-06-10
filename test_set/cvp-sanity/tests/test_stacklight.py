import json
import requests
import datetime
import pytest

@pytest.mark.sl_dup
#ElasticsearchClusterHealthStatusMajor or stacklight-pytest
@pytest.mark.full
@pytest.mark.usefixtures('check_kibana')
def test_elasticsearch_cluster(local_salt_client):
    salt_output = local_salt_client.pillar_get(
        tgt='kibana:server',
        param='_param:haproxy_elasticsearch_bind_host')
    ssl = local_salt_client.pillar_get(
        tgt='elasticsearch:server',
        param='haproxy:proxy:listen:elasticsearch:binds:ssl:enabled')
    proto = "https" if ssl else "http"

    proxies = {"http": None, "https": None}
    IP = salt_output
    assert requests.get('{0}://{1}:9200/'.format(proto, IP),
                        proxies=proxies, verify=False).status_code == 200, \
        'Cannot check elasticsearch url on {}.'.format(IP)
    resp = requests.get('{0}://{1}:9200/_cat/health'.format(proto, IP),
                        proxies=proxies, verify=False).content
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


@pytest.mark.sl_dup
#stacklight-pytest
@pytest.mark.full
@pytest.mark.usefixtures('check_kibana')
def test_kibana_status(local_salt_client):
    proxies = {"http": None, "https": None}
    IP = local_salt_client.pillar_get(param='_param:stacklight_log_address')
    ssl = local_salt_client.pillar_get(
        tgt='kibana:server',
        param='haproxy:proxy:listen:kibana:binds:ssl:enabled')
    proto = "https" if ssl else "http"

    resp = requests.get('{0}://{1}:5601/api/status'.format(proto, IP),
                        proxies=proxies, verify=False).content
    body = json.loads(resp)
    assert body['status']['overall']['state'] == "green", \
        "Kibana status is not expected: {}".format(
        body['status']['overall'])
    for i in body['status']['statuses']:
        assert i['state'] == "green", \
            "Kibana statuses are unexpected: {}".format(i)


@pytest.mark.smoke
#TODO: recheck
@pytest.mark.usefixtures('check_kibana')
def test_elasticsearch_node_count(local_salt_client):
    now = datetime.datetime.now()
    today = now.strftime("%Y.%m.%d")
    salt_output = local_salt_client.pillar_get(
        tgt='kibana:server',
        param='_param:haproxy_elasticsearch_bind_host')

    IP = salt_output
    ssl = local_salt_client.pillar_get(
        tgt='elasticsearch:server',
        param='haproxy:proxy:listen:elasticsearch:binds:ssl:enabled')
    proto = "https" if ssl else "http"

    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    proxies = {"http": None, "https": None}
    data = ('{"size": 0, "aggs": '
            '{"uniq_hostname": '
            '{"terms": {"size": 500, '
            '"field": "Hostname.keyword"}}}}')
    response = requests.post(
        '{0}://{1}:9200/log-{2}/_search?pretty'.format(proto, IP, today),
        proxies=proxies,
        headers=headers,
        verify = False,
        data=data)
    assert 200 == response.status_code, 'Unexpected code {}'.format(
        response.text)
    resp = json.loads(response.text)
    cluster_domain = local_salt_client.pillar_get(param='_param:cluster_domain')
    monitored_nodes = []
    for item_ in resp['aggregations']['uniq_hostname']['buckets']:
        node_name = item_['key']
        monitored_nodes.append(node_name + '.' + cluster_domain)
    missing_nodes = []
    all_nodes = local_salt_client.test_ping(tgt='*').keys()
    for node in all_nodes:
        if node not in monitored_nodes:
            missing_nodes.append(node)
    assert len(missing_nodes) == 0, \
        'Not all nodes are in Elasticsearch. Found {0} keys, ' \
        'expected {1}. Missing nodes: \n{2}'. \
            format(len(monitored_nodes), len(all_nodes), missing_nodes)


@pytest.mark.sl_dup
#DockerServiceMonitoring*
@pytest.mark.full
def test_stacklight_services_replicas(local_salt_client):
    # TODO
    # change to docker:swarm:role:master ?
    salt_output = local_salt_client.cmd(
        tgt='I@docker:client:stack:monitoring and I@prometheus:server',
        param='docker service ls',
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


@pytest.mark.smoke
@pytest.mark.usefixtures('check_prometheus')
def test_prometheus_alert_count(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:cluster_public_host')
    proto = local_salt_client.pillar_get(
        param='_param:cluster_public_protocol')
    # keystone:server can return 3 nodes instead of 1
    # this will be fixed later
    # TODO
    nodes_info = local_salt_client.cmd(
        tgt=ctl_nodes_pillar,
        param='curl -k -s {0}://{1}:15010/alerts | grep icon-chevron-down | '
              'grep -v "0 active"'.format(proto, IP),
        expr_form='pillar')

    result = nodes_info[nodes_info.keys()[0]].replace('</td>', '').replace(
        '<td><i class="icon-chevron-down"></i> <b>', '').replace('</b>', '')
    assert result == '', 'AlertManager page has some alerts! {}'.format(
                         json.dumps(result), indent=4)


@pytest.mark.sl_dup
#DockerServiceMonitoring* ??
@pytest.mark.full
def test_stacklight_containers_status(local_salt_client):
    salt_output = local_salt_client.cmd(
        tgt='I@docker:swarm:role:master and I@prometheus:server',
        param='docker service ps $(docker stack services -q monitoring)',
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


@pytest.mark.sl_dup
#PrometheusTargetDown
@pytest.mark.full
def test_running_telegraf_services(local_salt_client):
    salt_output = local_salt_client.cmd(tgt='telegraf:agent',
                                        fun='service.status',
                                        param='telegraf',
                                        expr_form='pillar',)

    if not salt_output:
        pytest.skip("Telegraf or telegraf:agent \
        pillar are not found on this environment.")

    result = [{node: status} for node, status
              in salt_output.items()
              if status is False]
    assert result == [], 'Telegraf service is not running ' \
                         'on following nodes: {}'.format(result)


@pytest.mark.sl_dup
#PrometheusTargetDown
@pytest.mark.full
def test_running_fluentd_services(local_salt_client):
    salt_output = local_salt_client.cmd(tgt='fluentd:agent',
                                        fun='service.status',
                                        param='td-agent',
                                        expr_form='pillar')
    result = [{node: status} for node, status
              in salt_output.items()
              if status is False]
    assert result == [], 'Fluentd check failed: td-agent service is not ' \
                         'running on following nodes:'.format(result)
