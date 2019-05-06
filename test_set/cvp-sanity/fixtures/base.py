import os
import pytest
import atexit
import utils
import logging

logging.basicConfig(
    filename="{dir}/full.log".format(
        dir=os.environ.get("PYTEST_REPORT_DIR") if os.environ.get("PYTEST_REPORT_DIR") else '.'
    ),
    level=logging.DEBUG,
    format='[%(asctime)-15s] [%(funcName)s:%(lineno)s]  %(message)s'
)


@pytest.fixture(autouse=True)
def add_testname_to_saltapi_logs(request):
    logging.info("\n{sep}\n {testname} \n{sep}\n".format(
        sep="*"*100,
        testname=request.node.name
    ))


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
    salt_output = local_salt_client.test_ping(tgt='keystone:server')
    if salt_output:
        return "keystone:server"
    else:
        salt_output = local_salt_client.test_ping(tgt='etcd:server')
        return "etcd:server" if salt_output else pytest.skip("Neither \
            Openstack nor k8s is found. Skipping test")


@pytest.fixture(scope='session')
def check_openstack(local_salt_client):
    salt_output = local_salt_client.test_ping(tgt='keystone:server')
    if not salt_output:
        pytest.skip("Openstack not found or keystone:server pillar \
          are not found on this environment.")


@pytest.fixture(scope='session')
def check_drivetrain(local_salt_client):
    salt_output = local_salt_client.test_ping(tgt='I@jenkins:client and not I@salt:master',
                                              expr_form='compound')
    if not salt_output:
        pytest.skip("Drivetrain service or jenkins:client pillar \
          are not found on this environment.")


@pytest.fixture(scope='session')
def check_prometheus(local_salt_client):
    salt_output = local_salt_client.test_ping(tgt='prometheus:server')
    if not salt_output:
        pytest.skip("Prometheus service or prometheus:server pillar \
          are not found on this environment.")


@pytest.fixture(scope='session')
def check_alerta(local_salt_client):
    salt_output = local_salt_client.test_ping(tgt='prometheus:alerta')
    if not salt_output:
        pytest.skip("Alerta service or prometheus:alerta pillar \
              are not found on this environment.")


@pytest.fixture(scope='session')
def check_kibana(local_salt_client):
    salt_output = local_salt_client.test_ping(tgt='kibana:server')
    if not salt_output:
        pytest.skip("Kibana service or kibana:server pillar \
          are not found on this environment.")


@pytest.fixture(scope='session')
def check_grafana(local_salt_client):
    salt_output = local_salt_client.test_ping(tgt='grafana:client')
    if not salt_output:
        pytest.skip("Grafana service or grafana:client pillar \
          are not found on this environment.")


@pytest.fixture(scope='session')
def check_cinder_backends(local_salt_client):
    backends_cinder_available = local_salt_client.test_ping(tgt='cinder:controller')
    if not backends_cinder_available or not any(backends_cinder_available.values()):
        pytest.skip("Cinder service or cinder:controller:backend pillar \
        are not found on this environment.")


def pytest_namespace():
    return {'contrail': None}


@pytest.fixture(scope='module')
def contrail(local_salt_client):
    probe = local_salt_client.cmd(
        tgt='opencontrail:control',
        fun='pillar.get',
        param='opencontrail:control:version',
        expr_form='pillar')
    if not probe:
        pytest.skip("Contrail is not found on this environment")
    versions = set(probe.values())
    if len(versions) != 1:
        pytest.fail('Contrail versions are not the same: {}'.format(probe))
    pytest.contrail = str(versions.pop())[:1]


@pytest.fixture(scope='session')
def check_kdt(local_salt_client):
    kdt_nodes_available = local_salt_client.test_ping(
        tgt="I@gerrit:client and I@kubernetes:pool and not I@salt:master",
        expr_form='compound'
    )
    if not kdt_nodes_available:
        pytest.skip("No 'kdt' nodes found. Skipping this test...")
    return kdt_nodes_available.keys()


@pytest.fixture(scope='session')
def check_kfg(local_salt_client):
    kfg_nodes_available = local_salt_client.cmd(
        tgt="I@kubernetes:pool and I@salt:master",
        expr_form='compound'
    )
    if not kfg_nodes_available:
        pytest.skip("No cfg-under-Kubernetes nodes found. Skipping this test...")
    return kfg_nodes_available.keys()


@pytest.fixture(scope='session')
def check_cicd(local_salt_client):
    cicd_nodes_available = local_salt_client.test_ping(
        tgt="I@gerrit:client and I@docker:swarm",
        expr_form='compound'
    )
    if not cicd_nodes_available:
        pytest.skip("No 'cid' nodes found. Skipping this test...")


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
            tgt='*',
            param='echo "NODE_INFO=$(uname -sr)" && ' + cat_image_version_file,
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
            logging.info(report_text)
        atexit.register(write_report)
        yield
    except Exception as e:
        logging.info("print_node_version:: some error occurred: {}".format(e))
        yield
