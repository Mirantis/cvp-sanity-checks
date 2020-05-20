import json
import requests
import datetime
import pytest

import utils
import logging

# ################################ FIXTURES ##################################


def prometheus_rules():
    salt = utils.init_salt_client()

    IP = salt.pillar_get(param='_param:cluster_public_host')
    proto = salt.pillar_get(
        param='_param:cluster_public_protocol')
    proxies = {"http": None, "https": None}

    prometheus_password = (
        # new password in 2019.2.7
        salt.pillar_get(
            tgt="nginx:server",
            param='_param:nginx_proxy_prometheus_server_password')

        # Generated password ~2019.2.4
        or salt.pillar_get(
            param='_param:prometheus_server_proxy_password_generated')

        # old password ~ 2019.2.0
        or salt.pillar_get(
            param='_param:keepalived_prometheus_vip_password_generated')

        or ""
    )

    if prometheus_password == "":
        logging.warning("Got empty prometheus_password. \
                        Possibly this cluster with no Stacklight component")
        return dict()

    response = requests.get(
        '{0}://{1}:15010/api/v1/rules'.format(proto, IP),
        proxies=proxies,
        auth=('prometheus', prometheus_password),
        verify=False)

    if not response.status_code == 200:
        logging.warning(
            "Got response with incorrect status: {}".format(response))
        return dict()

    content = json.loads(response.content.decode())
    rules = content['data']['groups'][0]["rules"]

    # collect rules with dict {'rulename' : {<rulecontent>}}
    alerts_by_name = {rule['name']: rule['alerts']
                      for rule in rules
                      }
    logging.debug("collected next rules: {}".format(alerts_by_name))
    return alerts_by_name


prometheus_rules = prometheus_rules()


@pytest.mark.usefixtures('check_prometheus')
@pytest.fixture(scope='session',
                ids=prometheus_rules.keys(),
                params=prometheus_rules.values())
def alert_in_prometheus(request):
    return request.param

# ############################## TESTS #######################################


@pytest.mark.sl_dup
# ElasticsearchClusterHealthStatusMajor or stacklight-pytest
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
        verify=False).content.decode()
    msg = "elasticsearch is not healthy:\n{}".format(
        json.dumps(response, indent=4))
    assert response.split()[3] == 'green', msg
    assert response.split()[4] == '3', msg
    assert response.split()[5] == '3', msg
    assert response.split()[10] == '0', msg
    assert response.split()[13] == '100.0%', msg


@pytest.mark.sl_dup
# stacklight-pytest
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
        verify=False).content.decode()
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
    cluster_domain = local_salt_client.pillar_get(
        param='_param:cluster_domain')
    monitored_nodes = []
    for item_ in resp['aggregations']['uniq_hostname']['buckets']:
        node_name = item_['key']
        monitored_nodes.append(node_name + '.' + cluster_domain)
    missing_nodes = []
    all_nodes = list(local_salt_client.test_ping(tgt='*').keys())
    for node in all_nodes:
        if node not in monitored_nodes:
            missing_nodes.append(node)
    assert len(missing_nodes) == 0, (
        "Not all nodes are in Elasticsearch. Expected {}, but found {} keys.\n"
        "Missing nodes:\n{}".format(
            len(monitored_nodes), len(all_nodes), missing_nodes)
    )


@pytest.mark.sl_dup
# DockerServiceMonitoring*
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
    for line in salt_output[list(salt_output.keys())[0]].split('\n'):
        if line[line.find('/') - 1] != line[line.find('/') + 1] \
           and 'replicated' in line:
            wrong_items.append(line)
    assert len(wrong_items) == 0, (
        "Some monitoring services don't have the expected number of "
        "replicas:\n{}".format(json.dumps(wrong_items, indent=4))
    )


@pytest.mark.smoke
def test_prometheus_alert_count(alert_in_prometheus):

    assert len(alert_in_prometheus) == 0, \
        '\n\n\tAlertManager page has some alerts!\n{} \n'.format(
            '\n'.join(
                [alert['annotations']['description']
                 for alert in alert_in_prometheus]
            ))


@pytest.mark.sl_dup
# DockerServiceMonitoring* ??
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
    if len(list(salt_output.keys())) > 1:
        if 'CURRENT STATE' not in salt_output[list(salt_output.keys())[0]]:
            del salt_output[list(salt_output.keys())[0]]
    for line in salt_output[list(salt_output.keys())[0]].split('\n')[1:]:
        shift = 0
        if line.split()[1] == '\\_':
            shift = 1
        if line.split()[1 + shift] not in list(result.keys()):
            result[line.split()[1]] = 'NOT OK'
        if line.split()[4 + shift] == 'Running' \
           or line.split()[4 + shift] == 'Ready':
            result[line.split()[1 + shift]] = 'OK'
    assert 'NOT OK' not in list(result.values()), (
        "Some containers have incorrect state:\n{}".format(
            json.dumps(result, indent=4))
    )


@pytest.mark.sl_dup
# PrometheusTargetDown
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
              in list(salt_output.items())
              if status is False]
    assert result == [], (
        "Telegraf service is not running on the following nodes:\n{}".format(
            result)
    )


@pytest.mark.sl_dup
# PrometheusTargetDown
@pytest.mark.full
def test_running_fluentd_services(local_salt_client):
    salt_output = local_salt_client.cmd(tgt='fluentd:agent',
                                        fun='service.status',
                                        param='td-agent',
                                        expr_form='pillar')
    result = [{node: status} for node, status
              in list(salt_output.items())
              if status is False]
    assert result == [], (
        "Fluentd check failed - td-agent service is not running on the "
        "following nodes:\n{}".format(result)
    )
