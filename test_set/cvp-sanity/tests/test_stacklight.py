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
    response = requests.get(
        '{0}://{1}:9200/'.format(proto, IP),
        proxies=proxies,
        verify=False)
    assert response.status_code == 200, (
        "Issues with accessing elasticsearch on {}.".format(IP))
    response = requests.get(
        '{0}://{1}:9200/_cat/health'.format(proto, IP),
        proxies=proxies,
        verify=False).content
    msg = "elasticsearch is not healthy:\n{}".format(
        json.dumps(response, indent=4))
    assert response.split()[3] == 'green',msg
    assert response.split()[4] == '3', msg
    assert response.split()[5] == '3', msg
    assert response.split()[10] == '0', msg
    assert response.split()[13] == '100.0%', msg


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

    response = requests.get(
        '{0}://{1}:5601/api/status'.format(proto, IP),
        proxies=proxies,
        verify=False).content
    body = json.loads(response)
    assert body['status']['overall']['state'] == "green", (
        "Kibana overall status is not 'green':\n{}".format(
            body['status']['overall'])
    )
    for i in body['status']['statuses']:
        assert i['state'] == "green", (
            "Kibana statuses are unexpected:\n{}".format(i))


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
        verify=False,
        data=data)
    assert response.status_code == 200, (
        'Issues with accessing elasticsearch on {}:\n{}'.format(
            IP, response.text)
    )
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
    assert len(missing_nodes) == 0, (
        "Not all nodes are in Elasticsearch. Expected {}, but found {} keys.\n"
        "Missing nodes:\n{}".format(
            len(monitored_nodes), len(all_nodes), missing_nodes)
    )


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
    assert len(wrong_items) == 0, (
        "Some monitoring services don't have the expected number of "
        "replicas:\n{}".format(json.dumps(wrong_items, indent=4))
    )


@pytest.mark.smoke
@pytest.mark.usefixtures('check_prometheus')
def test_prometheus_alert_count(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:cluster_public_host')
    prometheus_password_old = local_salt_client.pillar_get(
        param='_param:keepalived_prometheus_vip_password_generated')
    prometheus_password_generated = local_salt_client.pillar_get(
        param='_param:prometheus_server_proxy_password_generated')
    # New password in 2019.2.7
    prometheus_password_from_nginx =  local_salt_client.pillar_get(
        tgt="nginx:server",
        param='_param:nginx_proxy_prometheus_server_password')
    proto = local_salt_client.pillar_get(
        param='_param:cluster_public_protocol')
    proxies = {"http": None, "https": None}
    # keystone:server can return 3 nodes instead of 1
    # this will be fixed later
    # TODO
    if prometheus_password_from_nginx:
        prometheus_password = prometheus_password_from_nginx
    elif prometheus_password_generated:
        prometheus_password = prometheus_password_generated
    else:
        prometheus_password = prometheus_password_old

    response = requests.get(
        '{0}://{1}:15010/api/v1/alerts'.format(proto, IP),
        proxies=proxies,
        auth=('prometheus', prometheus_password))
    assert response.status_code == 200, (
        'Issues with accessing prometheus alerts on {}:\n{}'.format(
            IP, response.text)
    )
    alerts = json.loads(response.content)
    short_alerts = ''
    for i in alerts['data']['alerts']:
        short_alerts = '{}* {}\n'.format(short_alerts, i['annotations']['description'])
    assert alerts['data']['alerts'] == [], 'AlertManager page has some alerts!\n{}'.format(
        short_alerts)


@pytest.mark.sl_dup
#DockerServiceMonitoring* ??
@pytest.mark.full
def test_stacklight_containers_status(local_salt_client):
    salt_output = local_salt_client.cmd(
        tgt='I@docker:swarm:role:master and I@prometheus:server',
        param='docker service ps $(docker stack services -q monitoring)',
        expr_form='compound')

    if not salt_output:
        pytest.skip("docker:swarm:role:master or prometheus:server pillars "
                    "are not found on this environment.")

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
    assert 'NOT OK' not in result.values(), (
        "Some containers have incorrect state:\n{}".format(
            json.dumps(result, indent=4))
    )


@pytest.mark.sl_dup
#PrometheusTargetDown
@pytest.mark.full
def test_running_telegraf_services(local_salt_client):
    salt_output = local_salt_client.cmd(tgt='telegraf:agent',
                                        fun='service.status',
                                        param='telegraf',
                                        expr_form='pillar',)

    if not salt_output:
        pytest.skip("Telegraf or telegraf:agent pillars are not found on "
                    "this environment.")

    result = [{node: status} for node, status
              in salt_output.items()
              if status is False]
    assert result == [], (
        "Telegraf service is not running on the following nodes:\n{}".format(
            result)
    )


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
    assert result == [], (
        "Fluentd check failed - td-agent service is not running on the "
        "following nodes:\n{}".format(result)
    )
