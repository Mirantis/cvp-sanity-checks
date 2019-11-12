from builtins import str
import pytest
from fixtures.base import (
    print_node_version,
    check_cicd,
    check_kfg,
    check_kdt,
    contrail,
    check_cinder_backends,
    check_grafana,
    check_kibana,
    check_alerta,
    check_prometheus,
    check_openstack,
    check_ironic,
    check_drivetrain,
    check_openstack,
    ctl_nodes_pillar,
    nodes_in_group,
    local_salt_client,
    add_testname_to_saltapi_logs,)
import logging


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield

    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)
    rep.description = "{}".format(str(item.function.__doc__))
    setattr(item, 'description', item.function.__doc__)


@pytest.fixture(autouse=True)
def show_test_steps(request):
    yield
    # request.node is an "item" because we use the default
    # "function" scope
    if request.node.description is None or request.node.description == "None":
        return
    try:
        if request.node.rep_setup.failed:
            logging.warning("setup failed. The following steps were attempted: \n  {steps}".format(steps=request.node.description))
        elif request.node.rep_setup.passed:
            if request.node.rep_call.failed:
                logging.warning("test execution failed! The following steps were attempted: \n {steps}".format(steps=request.node.description))
    except BaseException as e:
        logging.info("Error in show_test_steps fixture: {}".format(e))
        pass
