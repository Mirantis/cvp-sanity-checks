from fixtures.base import *


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
            print("setup failed. The following steps were attempted: \n  {steps}".format(steps=request.node.description))
        elif request.node.rep_setup.passed:
            if request.node.rep_call.failed:
                print("test execution failed! The following steps were attempted: \n {steps}".format(steps=request.node.description))
    except BaseException as e:
        print("Error in show_test_steps fixture: {}".format(e))
        pass
