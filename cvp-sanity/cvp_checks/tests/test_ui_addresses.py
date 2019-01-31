from cvp_checks import utils
import pytest


@pytest.mark.usefixtures('check_openstack')
def test_ui_horizon(local_salt_client, ctl_nodes_pillar):
    salt_output = local_salt_client.cmd(
        'horizon:server',
        'pillar.get',
        ['_param:cluster_public_host'],
        expr_form='pillar')
    if not salt_output:
        pytest.skip("Horizon is not enabled on this environment")
    IP = [salt_output[node] for node in salt_output
          if salt_output[node]]
    result = local_salt_client.cmd(
        ctl_nodes_pillar,
        'cmd.run',
        ['curl --insecure https://{}/auth/login/ 2>&1 | \
         grep Login'.format(IP[0])],
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, \
        'Horizon login page is not reachable on {} from ctl nodes'.format(
        IP[0])


@pytest.mark.usefixtures('check_openstack')
def test_public_openstack(local_salt_client, ctl_nodes_pillar):
    IP = utils.get_monitoring_ip('cluster_public_host')
    protocol = 'https'
    port = '5000'
    url = "{}://{}:{}/v3".format(protocol, IP, port)
    result = local_salt_client.cmd(
        ctl_nodes_pillar,
        'cmd.run',
        ['curl -k {}/ 2>&1 | \
         grep stable'.format(url)],
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, \
        'Public Openstack url is not reachable on {} from ctl nodes'.format(url)


@pytest.mark.usefixtures('check_kibana')
def test_internal_ui_kibana(local_salt_client, ctl_nodes_pillar):
    IP = utils.get_monitoring_ip('stacklight_log_address')
    protocol = 'http'
    port = '5601'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        ctl_nodes_pillar,
        'cmd.run',
        ['curl {}/app/kibana 2>&1 | \
         grep loading'.format(url)],
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, \
        'Internal Kibana login page is not reachable on {} ' \
        'from ctl nodes'.format(url)


@pytest.mark.usefixtures('check_kibana')
def test_public_ui_kibana(local_salt_client, ctl_nodes_pillar):
    IP = utils.get_monitoring_ip('cluster_public_host')
    protocol = 'https'
    port = '5601'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        ctl_nodes_pillar,
        'cmd.run',
        ['curl {}/app/kibana 2>&1 | \
         grep loading'.format(url)],
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, \
        'Public Kibana login page is not reachable on {} ' \
        'from ctl nodes'.format(url)


@pytest.mark.usefixtures('check_prometheus')
def test_internal_ui_prometheus(local_salt_client, ctl_nodes_pillar):
    IP = utils.get_monitoring_ip('stacklight_monitor_address')
    protocol = 'http'
    port = '15010'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        ctl_nodes_pillar,
        'cmd.run',
        ['curl {}/graph 2>&1 | \
         grep Prometheus'.format(url)],
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, \
        'Internal Prometheus page is not reachable on {} ' \
        'from ctl nodes'.format(url)


@pytest.mark.usefixtures('check_prometheus')
def test_public_ui_prometheus(local_salt_client, ctl_nodes_pillar):
    IP = utils.get_monitoring_ip('cluster_public_host')
    protocol = 'https'
    port = '15010'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        ctl_nodes_pillar,
        'cmd.run',
        ['curl {}/graph 2>&1 | \
         grep Prometheus'.format(url)],
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, \
        'Public Prometheus page is not reachable on {} ' \
        'from ctl nodes'.format(url)


@pytest.mark.usefixtures('check_prometheus')
def test_internal_ui_alert_manager(local_salt_client, ctl_nodes_pillar):
    IP = utils.get_monitoring_ip('stacklight_monitor_address')
    protocol = 'http'
    port = '15011'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        ctl_nodes_pillar,
        'cmd.run',
        ['curl -s {}/ | grep Alertmanager'.format(url)],
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, \
        'Internal AlertManager page is not reachable on {} ' \
        'from ctl nodes'.format(url)


@pytest.mark.usefixtures('check_prometheus')
def test_public_ui_alert_manager(local_salt_client, ctl_nodes_pillar):
    IP = utils.get_monitoring_ip('cluster_public_host')
    protocol = 'https'
    port = '15011'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        ctl_nodes_pillar,
        'cmd.run',
        ['curl -s {}/ | grep Alertmanager'.format(url)],
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, \
        'Public AlertManager page is not reachable on {} ' \
        'from ctl nodes'.format(url)


@pytest.mark.usefixtures('check_grafana')
def test_internal_ui_grafana(local_salt_client, ctl_nodes_pillar):
    IP = utils.get_monitoring_ip('stacklight_monitor_address')
    protocol = 'http'
    port = '15013'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        ctl_nodes_pillar,
        'cmd.run',
        ['curl {}/login 2>&1 | grep Grafana'.format(url)],
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, \
        'Internal Grafana page is not reachable on {} ' \
        'from ctl nodes'.format(url)


@pytest.mark.usefixtures('check_grafana')
def test_public_ui_grafana(local_salt_client, ctl_nodes_pillar):
    IP = utils.get_monitoring_ip('cluster_public_host')
    protocol = 'https'
    port = '8084'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        ctl_nodes_pillar,
        'cmd.run',
        ['curl {}/login 2>&1 | grep Grafana'.format(url)],
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, \
        'Public Grafana page is not reachable on {} from ctl nodes'.format(url)


@pytest.mark.usefixtures('check_alerta')
def test_internal_ui_alerta(local_salt_client, ctl_nodes_pillar):
    IP = utils.get_monitoring_ip('stacklight_monitor_address')
    protocol = 'http'
    port = '15017'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        ctl_nodes_pillar,
        'cmd.run',
        ['curl {}/ 2>&1 | \
         grep Alerta'.format(url)],
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, \
        'Internal Alerta page is not reachable on {} from ctl nodes'.format(url)


@pytest.mark.usefixtures('check_alerta')
def test_public_ui_alerta(local_salt_client, ctl_nodes_pillar):
    IP = utils.get_monitoring_ip('cluster_public_host')
    protocol = 'https'
    port = '15017'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        ctl_nodes_pillar,
        'cmd.run',
        ['curl {}/ 2>&1 | \
         grep Alerta'.format(url)],
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, \
        'Public Alerta page is not reachable on {} from ctl nodes'.format(url)


@pytest.mark.usefixtures('check_drivetrain')
def test_public_ui_jenkins(local_salt_client, ctl_nodes_pillar):
    IP = utils.get_monitoring_ip('cluster_public_host')
    protocol = 'https'
    port = '8081'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        ctl_nodes_pillar,
        'cmd.run',
        ['curl -k {}/ 2>&1 | \
         grep Authentication'.format(url)],
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, \
        'Public Jenkins page is not reachable on {} from ctl nodes'.format(url)


@pytest.mark.usefixtures('check_drivetrain')
def test_public_ui_gerrit(local_salt_client, ctl_nodes_pillar):
    IP = utils.get_monitoring_ip('cluster_public_host')
    protocol = 'https'
    port = '8070'
    url = "{}://{}:{}".format(protocol, IP, port)
    result = local_salt_client.cmd(
        ctl_nodes_pillar,
        'cmd.run',
        ['curl -k {}/ 2>&1 | \
         grep "Gerrit Code Review"'.format(url)],
        expr_form='pillar')
    assert len(result[result.keys()[0]]) != 0, \
        'Public Gerrit page is not reachable on {} from ctl nodes'.format(url)
