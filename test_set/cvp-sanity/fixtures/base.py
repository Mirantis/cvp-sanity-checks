import pytest
import atexit
import utils


@pytest.fixture(scope='session')
def local_salt_client():
    return utils.init_salt_client()

nodes = utils.calculate_groups()


@pytest.fixture(scope='session', params=nodes.values(), ids=nodes.keys())
def nodes_in_group(request):
    return request.param


@pytest.fixture(scope='session')
def ctl_nodes_pillar(local_salt_client):
    '''Return controller node pillars (OS or k8s ctls).
       This will help to identify nodes to use for UI curl tests.
       If no platform is installed (no OS or k8s) we need to skip
       the test (product team use case).
    '''
    salt_output = local_salt_client.cmd(
        'keystone:server',
        'test.ping',
        expr_form='pillar')
    if salt_output:
        return "keystone:server"
    else:
        salt_output = local_salt_client.cmd(
            'etcd:server',
            'test.ping',
            expr_form='pillar')
        return "etcd:server" if salt_output else pytest.skip("Neither \
            Openstack nor k8s is found. Skipping test")


@pytest.fixture(scope='session')
def check_openstack(local_salt_client):
    salt_output = local_salt_client.cmd(
        'keystone:server',
        'test.ping',
        expr_form='pillar')
    if not salt_output:
        pytest.skip("Openstack not found or keystone:server pillar \
          are not found on this environment.")


@pytest.fixture(scope='session')
def check_drivetrain(local_salt_client):
    salt_output = local_salt_client.cmd(
        'I@jenkins:client and not I@salt:master',
        'test.ping',
        expr_form='compound')
    if not salt_output:
        pytest.skip("Drivetrain service or jenkins:client pillar \
          are not found on this environment.")


@pytest.fixture(scope='session')
def check_prometheus(local_salt_client):
    salt_output = local_salt_client.cmd(
        'prometheus:server',
        'test.ping',
        expr_form='pillar')
    if not salt_output:
        pytest.skip("Prometheus service or prometheus:server pillar \
          are not found on this environment.")


@pytest.fixture(scope='session')
def check_alerta(local_salt_client):
    salt_output = local_salt_client.cmd(
        'prometheus:alerta',
        'test.ping',
        expr_form='pillar')
    if not salt_output:
        pytest.skip("Alerta service or prometheus:alerta pillar \
              are not found on this environment.")


@pytest.fixture(scope='session')
def check_kibana(local_salt_client):
    salt_output = local_salt_client.cmd(
        'kibana:server',
        'test.ping',
        expr_form='pillar')
    if not salt_output:
        pytest.skip("Kibana service or kibana:server pillar \
          are not found on this environment.")


@pytest.fixture(scope='session')
def check_grafana(local_salt_client):
    salt_output = local_salt_client.cmd(
        'grafana:client',
        'test.ping',
        expr_form='pillar')
    if not salt_output:
        pytest.skip("Grafana service or grafana:client pillar \
          are not found on this environment.")


def pytest_namespace():
    return {'contrail': None}


@pytest.fixture(scope='module')
def contrail(local_salt_client):
    probe = local_salt_client.cmd(
        'opencontrail:control',
        'pillar.get',
        'opencontrail:control:version',
        expr_form='pillar')
    if not probe:
        pytest.skip("Contrail is not found on this environment")
    versions = set(probe.values())
    if len(versions) != 1:
        pytest.fail('Contrail versions are not the same: {}'.format(probe))
    pytest.contrail = str(versions.pop())[:1]


@pytest.fixture(autouse=True, scope='session')
def print_node_version(local_salt_client):
    """
        Gets info about each node using salt command, info is represented as a dictionary with :
        {node_name1: output1, node_name2: ...}

        :print to output the table with results after completing all tests if nodes and salt output exist.
                Prints nothing otherwise
        :return None
    """
    try:
        filename_with_versions = "/etc/image_version"
        cat_image_version_file = "if [ -f '{name}' ]; then \
                                        cat {name}; \
                                    else \
                                        echo BUILD_TIMESTAMP='no {name}'; \
                                        echo BUILD_TIMESTAMP_RFC='no {name}'; \
                                    fi ".format(name=filename_with_versions)

        list_version = local_salt_client.cmd(
            '*',
            'cmd.run',
            'echo "NODE_INFO=$(uname -sr)" && ' + cat_image_version_file,
            expr_form='compound')
        if list_version.__len__() == 0:
            yield
        parsed = {k: v.split('\n') for k, v in list_version.items()}
        columns = [name.split('=')[0] for name in parsed.values()[0]]

        template = "{:<40} | {:<25} | {:<25} | {:<25}\n"

        report_text = template.format("NODE", *columns)
        for node, data in sorted(parsed.items()):
            report_text += template.format(node, *[item.split("=")[1] for item in data])

        def write_report():
            print(report_text)
        atexit.register(write_report)
        yield
    except Exception as e:
        print("print_node_version:: some error occurred: {}".format(e))
        yield
