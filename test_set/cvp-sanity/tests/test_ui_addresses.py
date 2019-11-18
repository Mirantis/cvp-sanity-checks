import requests
import pytest


@pytest.mark.smoke
@pytest.mark.usefixtures('check_openstack')
def test_ui_horizon(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(
        tgt='horizon:server',
        param='_param:cluster_public_host')
    proto = local_salt_client.pillar_get(
        param='_param:cluster_public_protocol')
    if not IP:
        pytest.skip("Horizon is not enabled on this environment")
    result = local_salt_client.cmd_any(
        tgt=ctl_nodes_pillar,
        param='curl -k {0}://{1}/auth/login/ 2>&1 | \
               grep Login'.format(proto, IP),
        expr_form='pillar')
    assert len(result) != 0, (
        'Horizon login page is not reachable on {} from ctl nodes.'.format(IP))


@pytest.mark.smoke
@pytest.mark.usefixtures('check_openstack')
def test_public_openstack(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:cluster_public_host')
    proto = local_salt_client.pillar_get(
        param='_param:cluster_public_protocol')
    port = '5000'
    url = "{}://{}:{}/v3".format(proto, IP, port)
    result = local_salt_client.cmd(
        tgt=ctl_nodes_pillar,
        param='curl -k {}/ 2>&1 | grep stable'.format(url),
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, (
        'Public Openstack url is not reachable on {} from ctl '
        'nodes'.format(url)
    )


@pytest.mark.sl_dup
#stacklight-pytest?
@pytest.mark.full
@pytest.mark.usefixtures('check_kibana')
def test_internal_ui_kibana(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:stacklight_log_address')
    ssl = local_salt_client.pillar_get(
        tgt='kibana:server',
        param='haproxy:proxy:listen:kibana:binds:ssl:enabled')
    proto = "https" if ssl == "True" else "http"
    port = '5601'
    url = "{}://{}:{}".format(proto, IP, port)
    result = local_salt_client.cmd(
        tgt=ctl_nodes_pillar,
        param='curl -k {}/app/kibana 2>&1 | grep loading'.format(url),
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, (
        'Internal Kibana login page is not reachable on {} from ctl '
        'nodes'.format(url)
    )


@pytest.mark.smoke
@pytest.mark.usefixtures('check_kibana')
def test_public_ui_kibana(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:cluster_public_host')
    proto = local_salt_client.pillar_get(
        param='_param:cluster_public_protocol')
    port = '5601'
    url = "{}://{}:{}".format(proto, IP, port)
    result = local_salt_client.cmd(
        tgt=ctl_nodes_pillar,
        param='curl -k {}/app/kibana 2>&1 | grep loading'.format(url),
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, (
        'Public Kibana login page is not reachable on {} from ctl '
        'nodes'.format(url)
    )


@pytest.mark.sl_dup
#stacklight-pytest?
@pytest.mark.full
@pytest.mark.usefixtures('check_prometheus')
def test_internal_ui_prometheus(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:stacklight_monitor_address')
    protocol = 'http'
    port = '15010'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        tgt=ctl_nodes_pillar,
        param='curl {}/graph 2>&1 | grep Prometheus'.format(url),
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, (
        'Internal Prometheus page is not reachable on {} from ctl '
        'nodes'.format(url)
    )


@pytest.mark.smoke
@pytest.mark.usefixtures('check_prometheus')
def test_public_ui_prometheus(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:cluster_public_host')
    prometheus_password_old = local_salt_client.pillar_get(
        param='_param:keepalived_prometheus_vip_password_generated')
    prometheus_password = local_salt_client.pillar_get(
        param='_param:prometheus_server_proxy_password_generated')
    proto = local_salt_client.pillar_get(
        param='_param:cluster_public_protocol')
    proxies = {"http": None, "https": None}
    if prometheus_password == '':
        prometheus_password = prometheus_password_old
    response = requests.get(
        '{0}://{1}:15010/graph'.format(proto, IP),
        proxies=proxies,
        auth=('prometheus', prometheus_password))
    assert response.status_code == 200, (
        'Issues with accessing public prometheus ui on {}:\n{}'.format(
            IP, response.text)
    )
    assert response.content.find('Prometheus Time Series Collection') > -1, (
        'Public Prometheus page is not reachable on {} from ctl '
        'nodes'.format(url)
    )


@pytest.mark.sl_dup
#stacklight-pytest?
@pytest.mark.full
@pytest.mark.usefixtures('check_prometheus')
def test_internal_ui_alert_manager(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:stacklight_monitor_address')
    protocol = 'http'
    port = '15011'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        tgt=ctl_nodes_pillar,
        param='curl -s {}/ | grep Alertmanager'.format(url),
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, (
        'Internal AlertManager page is not reachable on {} from ctl '
        'nodes'.format(url)
    )


@pytest.mark.smoke
@pytest.mark.usefixtures('check_prometheus')
def test_public_ui_alert_manager(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:cluster_public_host')
    alermanager_password_old = local_salt_client.pillar_get(
        param='_param:keepalived_prometheus_vip_password_generated')
    alermanager_password = local_salt_client.pillar_get(
        param='_param:prometheus_alermanager_proxy_password_generated')
    proto = local_salt_client.pillar_get(
        param='_param:cluster_public_protocol')
    proxies = {"http": None, "https": None}
    if alermanager_password == '':
        alermanager_password = alermanager_password_old
    response = requests.get(
        '{0}://{1}:15011/'.format(proto, IP),
        proxies=proxies,
        auth=('alertmanager', alermanager_password))
    assert response.status_code == 200, (
        'Issues with accessing public alert manager ui on {}:\n{}'.format(
            IP, response.text)
    )
    assert response.content.find('<title>Alertmanager</title>') > -1, (
        'Public AlertManager page is not reachable on {} '
        'from ctl nodes'.format(url)
    )


@pytest.mark.sl_dup
#stacklight-pytest?
@pytest.mark.full
@pytest.mark.usefixtures('check_grafana')
def test_internal_ui_grafana(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:stacklight_monitor_address')
    protocol = 'http'
    port = '15013'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        tgt=ctl_nodes_pillar,
        param='curl {}/login 2>&1 | grep Grafana'.format(url),
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, (
        'Internal Grafana page is not reachable on {} '
        'from ctl nodes'.format(url)
    )


@pytest.mark.smoke
@pytest.mark.usefixtures('check_grafana')
def test_public_ui_grafana(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:cluster_public_host')
    proto = local_salt_client.pillar_get(
        param='_param:cluster_public_protocol')
    port = '8084'
    url = "{}://{}:{}".format(proto, IP, port)
    result = local_salt_client.cmd(
        tgt=ctl_nodes_pillar,
        param='curl -k {}/login 2>&1 | grep Grafana'.format(url),
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, (
        'Public Grafana page is not reachable on {} from ctl nodes'.format(url)
    )


@pytest.mark.sl_dup
#stacklight-pytest?
@pytest.mark.full
@pytest.mark.usefixtures('check_alerta')
def test_internal_ui_alerta(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:stacklight_monitor_address')
    protocol = 'http'
    port = '15017'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        tgt=ctl_nodes_pillar,
        param='curl {}/ 2>&1 | grep Alerta'.format(url),
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, (
        'Internal Alerta page is not reachable on {} from '
        'ctl nodes'.format(url)
    )


@pytest.mark.smoke
@pytest.mark.usefixtures('check_alerta')
def test_public_ui_alerta(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:cluster_public_host')
    proto = local_salt_client.pillar_get(
        param='_param:cluster_public_protocol')
    port = '15017'
    url = "{}://{}:{}".format(proto, IP, port)
    result = local_salt_client.cmd(
        tgt=ctl_nodes_pillar,
        param='curl -k {}/ 2>&1 | grep Alerta'.format(url),
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, (
        'Public Alerta page is not reachable on {} from ctl nodes'.format(url))


@pytest.mark.smoke
@pytest.mark.usefixtures('check_openstack')
@pytest.mark.usefixtures('check_drivetrain')
def test_public_ui_jenkins(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:cluster_public_host')
    proto = local_salt_client.pillar_get(
        param='_param:cluster_public_protocol')
    port = '8081'
    url = "{}://{}:{}".format(proto, IP, port)
    result = local_salt_client.cmd(
        tgt=ctl_nodes_pillar,
        param='curl -k {}/ 2>&1 | grep Authentication'.format(url),
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, (
        'Public Jenkins page is not reachable on {} from ctl nodes'.format(url)
    )


@pytest.mark.smoke
@pytest.mark.usefixtures('check_openstack')
@pytest.mark.usefixtures('check_drivetrain')
def test_public_ui_gerrit(local_salt_client, ctl_nodes_pillar):
    IP = local_salt_client.pillar_get(param='_param:cluster_public_host')
    proto = local_salt_client.pillar_get(
        param='_param:cluster_public_protocol')
    port = '8070'
    url = "{}://{}:{}".format(proto, IP, port)
    result = local_salt_client.cmd(
        tgt=ctl_nodes_pillar,
        param='curl -k {}/ 2>&1 | grep "Gerrit Code Review"'.format(url),
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, (
        'Public Gerrit page is not reachable on {} from ctl nodes'.format(url))
