import git
import jenkins
import json
import logging
import os
import pytest
import time
import utils
from builtins import range
from ldap3 import (
    Connection,
    Server,
    Reader,
    LDIF,
    MODIFY_ADD,
    MODIFY_DELETE,
    SUBTREE,
    ALL_ATTRIBUTES)
from ldap3.core.exceptions import LDAPException
from pygerrit2 import GerritRestAPI, HTTPBasicAuth
from requests import HTTPError
from xml.dom import minidom
from collections import defaultdict

# ############################ FIXTURES ######################################
user_name = 'DT_test_user'
user_pass = 'aSecretPassw'


def join_to_gerrit(local_salt_client, gerrit_user, gerrit_password):
    # Workaround for issue in test_drivetrain.join_to_jenkins https://github.com/kennethreitz/requests/issues/3829
    os.environ["PYTHONHTTPSVERIFY"] = "0"

    pytest.gerrit_port = local_salt_client.pillar_get(
        tgt='I@gerrit:client and not I@salt:master',
        param='_param:haproxy_gerrit_bind_port',
        expr_form='compound')
    pytest.gerrit_address = local_salt_client.pillar_get(
        tgt='I@gerrit:client and not I@salt:master',
        param='_param:haproxy_gerrit_bind_host',
        expr_form='compound')

    pytest.gerrit_protocol = local_salt_client.pillar_get(
        tgt='I@gerrit:client and not I@salt:master',
        param="gerrit:client:server:protocol",
        expr_form='compound')

    gerrit_url = '{protocol}://{address}:{port}'.format(
        protocol=pytest.gerrit_protocol,
        address=pytest.gerrit_address,
        port=pytest.gerrit_port)
    auth = HTTPBasicAuth(gerrit_user, gerrit_password)
    rest = GerritRestAPI(url=gerrit_url, auth=auth)
    return rest


def join_to_jenkins(local_salt_client, jenkins_user, jenkins_password):

    pytest.jenkins_port = local_salt_client.pillar_get(
        tgt='I@jenkins:client and not I@salt:master',
        param='_param:haproxy_jenkins_bind_port',
        expr_form='compound')
    pytest.jenkins_address = local_salt_client.pillar_get(
        tgt='I@jenkins:client and not I@salt:master',
        param='_param:haproxy_jenkins_bind_host',
        expr_form='compound')
    pytest.jenkins_protocol = local_salt_client.pillar_get(
        tgt='I@gerrit:client and not I@salt:master',
        param="_param:jenkins_master_protocol",
        expr_form='compound')

    jenkins_url = '{protocol}://{address}:{port}'.format(
        protocol=pytest.jenkins_protocol,
        address=pytest.jenkins_address,
        port=pytest.jenkins_port)
    server = jenkins.Jenkins(jenkins_url, username=jenkins_user, password=jenkins_password)
    return server


def get_password(local_salt_client,service):
    password = local_salt_client.pillar_get(
        tgt=service,
        param='_param:openldap_admin_password')
    return password


@pytest.fixture(scope='class')
def ldap_conn_from_new_admin(local_salt_client):
    """
      1. Create a test user 'DT_test_user' in openldap
      2. Add the user to admin group

    :return:  connection to ldap with new created user
    Finally, delete the user from admin group and openldap
    """
    ldap_password = get_password(local_salt_client, 'openldap:client')
    # Check that ldap_password is exists, otherwise skip test
    if not ldap_password:
        pytest.skip("Openldap service or openldap:client pillar \
        are not found on this environment.")
    ldap_port = local_salt_client.pillar_get(
        tgt='I@openldap:client and not I@salt:master',
        param='_param:haproxy_openldap_bind_port',
        expr_form='compound')
    ldap_address = local_salt_client.pillar_get(
        tgt='I@openldap:client and not I@salt:master',
        param='_param:haproxy_openldap_bind_host',
        expr_form='compound')
    ldap_dc = local_salt_client.pillar_get(
        tgt='openldap:client',
        param='_param:openldap_dn')
    ldap_admin_name = local_salt_client.pillar_get(
        tgt='openldap:client',
        param='openldap:client:server:auth:user')
    ldap_admin_password = local_salt_client.pillar_get(
        tgt='openldap:client',
        param='openldap:client:server:auth:password')

    ldap_user_name = 'cn={0},ou=people,{1}'.format(user_name, ldap_dc)

    # Admins group CN
    admin_gr_dn = 'cn=admins,ou=groups,{0}'.format(ldap_dc)
    # List of attributes for test user
    attrs = {
        'cn': user_name,
        'sn': user_name,
        'uid': user_name,
        'userPassword': user_pass,
        'objectClass': ['shadowAccount', 'inetOrgPerson'],
        'description': 'Test user for CVP DT test'
    }
    logging.warning("LOCALS  {}".format(locals()))
    ldap_server = Server(host=ldap_address, port=ldap_port,
                         use_ssl=False, get_info='NO_INFO')
    admin_conn = Connection(ldap_server,
                            user=ldap_admin_name,
                            password=ldap_admin_password)

    admin_conn.bind()
    # Add new user
    new_user = admin_conn.add(ldap_user_name, 'person', attrs)
    if not new_user:
        logging.warning('new_user: {}\n error: {}'.format(new_user,
                                                          admin_conn.result))
    # Add him to admins group
    modified_user = admin_conn.modify(admin_gr_dn,
                                      {'memberUid': (MODIFY_ADD, [user_name])})
    if not modified_user:
        logging.warning("added user to admins: {} \n error: {}".format(
            modified_user,
            admin_conn.result))

    user_conn = Connection(ldap_server,
                           user=ldap_user_name,
                           password=user_pass)
    user_conn.bind()

    # ###########################
    yield user_conn
    # ###########################
    user_conn.unbind()
    admin_conn.modify(admin_gr_dn, {
        'memberUid': (MODIFY_DELETE, [user_name])
    })
    admin_conn.delete(ldap_user_name)
    admin_conn.unbind()

# ########################### TESTS ##########################################


@pytest.mark.full
def test_drivetrain_gerrit(local_salt_client, check_cicd):

    gerrit_password = get_password(local_salt_client, 'gerrit:client')
    gerrit_error = ''
    current_date = time.strftime("%Y%m%d-%H.%M.%S", time.localtime())
    test_proj_name = "test-dt-{0}".format(current_date)

    try:
        # Connecting to gerrit and check connection
        server = join_to_gerrit(local_salt_client, 'admin', gerrit_password)
        gerrit_check = server.get("/changes/?q=owner:self%20status:open")
        # Check deleteproject plugin and skip test if the plugin is not installed
        gerrit_plugins = server.get("/plugins/?all")
        if 'deleteproject' not in gerrit_plugins:
            pytest.skip("Delete-project plugin is not installed")
        # Create test project and add description
        server.put("/projects/"+test_proj_name)
        server.put("/projects/"+test_proj_name+"/description",
                   json={"description": "Test DriveTrain project", "commit_message": "Update the project description"})
    except HTTPError as e:
        gerrit_error = e
    try:
        # Create test folder and init git
        repo_dir = os.path.join(os.getcwd(),test_proj_name)
        file_name = os.path.join(repo_dir, current_date)
        repo = git.Repo.init(repo_dir)
        # Add remote url for this git repo
        origin = repo.create_remote('origin', '{http}://admin:{password}@{address}:{port}/{project}.git'.format(
            project=test_proj_name,
            password=gerrit_password,
            http=pytest.gerrit_protocol,
            address=pytest.gerrit_address,
            port=pytest.gerrit_port))
        # Add commit-msg hook to automatically add Change-Id to our commit
        os.system("curl -Lo {repo}/.git/hooks/commit-msg '{http}://admin:{password}@{address}:{port}/tools/hooks/commit-msg' > /dev/null 2>&1".format(
            repo=repo_dir,
            password=gerrit_password,
            address=pytest.gerrit_address,
            http=pytest.gerrit_protocol,
            port=pytest.gerrit_port))
        os.system("chmod u+x {0}/.git/hooks/commit-msg".format(repo_dir))
        # Create a test file
        f = open(file_name, 'w+')
        f.write("This is a test file for DriveTrain test")
        f.close()
        # Add file to git and commit it to Gerrit for review
        repo.index.add([file_name])
        repo.index.commit("This is a test commit for DriveTrain test")
        repo.git.push("origin", "HEAD:refs/for/master")
        # Get change id from Gerrit. Set Code-Review +2 and submit this change
        changes = server.get("/changes/?q=project:{0}".format(test_proj_name))
        last_change = changes[0].get('change_id')
        server.post("/changes/{0}/revisions/1/review".format(last_change), json={"message": "All is good","labels":{"Code-Review":"+2"}})
        server.post("/changes/{0}/submit".format(last_change))
    except HTTPError as e:
        gerrit_error = e
    finally:
        # Delete test project
        server.post("/projects/"+test_proj_name+"/deleteproject~delete")
    assert gerrit_error == '', (
        'There is an error during Gerrit operations:\n{}'.format(gerrit_error))


@pytest.mark.usefixtures('ldap_conn_from_new_admin')
class TestOpenldap():
    @pytest.mark.full
    def test_new_user_can_connect_jenkins(self, local_salt_client, check_cicd):
        """
             1. Start job in jenkins from new ldap user
        """
        # Get a test job name from config
        config = utils.get_configuration()
        jenkins_cvp_job = config['jenkins_cvp_job']
        jenkins_error = ''
        try:
            # Check connection between Jenkins and LDAP
            jenkins_server = join_to_jenkins(local_salt_client, user_name, user_pass)
            jenkins_version = jenkins_server.get_job_name(jenkins_cvp_job)
        except jenkins.JenkinsException as e:
            jenkins_error = e
        assert jenkins_error == '', (
            "Connection to Jenkins is not established:\n{}".format(jenkins_error))

    @pytest.mark.full
    def test_new_user_can_connect_gerrit(self, local_salt_client, check_cicd):
        """
             1. Add the user to devops group in Gerrit
             2. Login to Gerrit using test_user credentials.

        """
        ldap_password = get_password(local_salt_client, 'openldap:client')
        gerrit_error = ''

        try:
            # Check connection between Gerrit and LDAP
            gerrit_server = join_to_gerrit(local_salt_client, 'admin', ldap_password)
            gerrit_check = gerrit_server.get("/changes/?q=owner:self%20status:open")

            # Add test user to devops-contrib group in Gerrit and check login
            _link = "/groups/devops-contrib/members/{0}".format(user_name)
            gerrit_add_user = gerrit_server.put(_link)

            # Login to Gerrit as a user
            gerrit_server = join_to_gerrit(local_salt_client, user_name, user_pass)
            gerrit_result = gerrit_server.get(
                "/changes/?q=owner:self%20status:open")
        except HTTPError as e:
            gerrit_error = e

        assert gerrit_error == '', (
            "Connection to Gerrit is not established:\n{}".format(gerrit_error))


@pytest.mark.sl_dup
#DockerService***Outage
@pytest.mark.full
def test_drivetrain_services_replicas(local_salt_client, check_cicd):
    """
        # Execute ` salt -C 'I@gerrit:client' cmd.run 'docker service ls'` command to get info  for each docker service like that:
        "x5nzktxsdlm6        jenkins_slave02     replicated          0/1                 docker-prod-local.artifactory.mirantis.com/mirantis/cicd/jnlp-slave:2019.2.0         "
        # Check that each service has all replicas
    """
    # TODO: replace with rerunfalures plugin
    wrong_items = []
    for _ in range(4):
        docker_services_by_nodes = local_salt_client.cmd(
            tgt='I@gerrit:client',
            param='docker service ls',
            expr_form='compound')
        wrong_items = []
        for line in docker_services_by_nodes[list(docker_services_by_nodes.keys())[0]].split('\n'):
            if line[line.find('/') - 1] != line[line.find('/') + 1] \
               and 'replicated' in line:
                wrong_items.append(line)
        if len(wrong_items) == 0:
            break
        else:
            time.sleep(5)
    assert len(wrong_items) == 0, (
        "Some DriveTrain services don't have expected number of replicas:\n"
        "{}".format(json.dumps(wrong_items, indent=4))
    )


@pytest.mark.full
def test_drivetrain_components_and_versions(local_salt_client, check_cicd):
    """
        1. Execute command `docker service ls --format "{{.Image}}"'` on  the 'I@gerrit:client' target
        2. Execute  ` salt -C 'I@gerrit:client' pillar.get docker:client:images`
        3. Check that list of images from step 1 is the same as a list from the step2
        4. Check that all docker services has label that equals to mcp_version

    """
    def get_name(long_name):
        return long_name.rsplit(':', 1)[0]

    def get_tag(long_name):
        return long_name.rsplit(':', 1)[-1]

    table_with_docker_services = local_salt_client.cmd(tgt='I@gerrit:client',
                                                       param='docker service ls --format "{{.Image}}"',
                                                       expr_form='compound')
    stack_info = local_salt_client.pillar_get(tgt='gerrit:client',
                                                   param='docker:client:stack')

    expected_images_list = list()
    # find services in list of docker clients
    for key, stack in list(stack_info.items()):
        if stack.get('service'):
            stack = [item.get('image') for _, item in
                     list(stack.get('service').items()) if item.get('image')]
            expected_images_list += stack
    expected_images = defaultdict(list)

    # collect unique tags for each image in same structure as for actual images
    for image in expected_images_list:
        if get_name(image) in expected_images:
            if get_tag(image) not in expected_images[get_name(image)]:
                expected_images[get_name(image)].append(get_tag(image))
        else:
            expected_images[get_name(image)].append(get_tag(image))

    # collect tags for each image in same structure as for expected images
    actual_images = defaultdict(list)
    for image in set(table_with_docker_services[
                         list(table_with_docker_services.keys())[0]].split('\n')):
        actual_images[get_name(image)].append(get_tag(image))

    # find difference between defaultdicts
    total_diff = 0
    for i in expected_images:
        diff = set(expected_images[i]) - set(actual_images[i])
        total_diff += len(diff)

    assert actual_images == expected_images, (
        "Some DriveTrain components do not have expected versions:\n{}".format(
            json.dumps(total_diff, indent=4))
    )


@pytest.mark.full
def test_jenkins_jobs_branch(local_salt_client, check_cicd):
    """ This test compares Jenkins jobs versions
        collected from the cloud vs collected from pillars.
    """

    excludes = ['upgrade-mcp-release', 'deploy-update-salt',
                'git-mirror-downstream-mk-pipelines',
                'git-mirror-downstream-pipeline-library']

    config = utils.get_configuration()
    drivetrain_version = config.get('drivetrain_version', '')
    jenkins_password = get_password(local_salt_client, 'jenkins:client')
    version_mismatch = []
    server = join_to_jenkins(local_salt_client, 'admin', jenkins_password)
    for job_instance in server.get_jobs():
        job_name = job_instance.get('name')
        if job_name in excludes:
            continue

        job_config = server.get_job_config(job_name)
        xml_data = minidom.parseString(job_config)
        BranchSpec = xml_data.getElementsByTagName('hudson.plugins.git.BranchSpec')

        # We use master branch for pipeline-library in case of 'testing,stable,nighlty' versions
        # Leave proposed version as is
        # in other cases we get release/{drivetrain_version}  (e.g release/2019.2.0)
        if drivetrain_version in ['testing', 'nightly', 'stable']:
            expected_version = 'master'
        else:
            expected_version = local_salt_client.pillar_get(
                tgt='gerrit:client',
                param='jenkins:client:job:{}:scm:branch'.format(job_name))

        if not BranchSpec:
            logging.debug("No BranchSpec has found for {} job".format(job_name))
            continue

        actual_version = BranchSpec[0].getElementsByTagName('name')[0].childNodes[0].data
        if expected_version and actual_version not in expected_version:
            version_mismatch.append("Job {0} has {1} branch."
                                    "Expected {2}".format(job_name,
                                                          actual_version,
                                                          expected_version))
    assert len(version_mismatch) == 0, (
        "Some DriveTrain jobs have version/branch mismatch:\n{}".format(
            json.dumps(version_mismatch, indent=4))
    )


@pytest.mark.full
def test_drivetrain_jenkins_job(local_salt_client, check_cicd):
    """
        # Login to Jenkins on jenkins:client
        # Read the name of jobs from configuration 'jenkins_test_job'
        # Start job
        # Wait till the job completed
        # Check that job has completed with "SUCCESS" result
    """
    job_result = None

    jenkins_password = get_password(local_salt_client, 'jenkins:client')
    server = join_to_jenkins(local_salt_client, 'admin', jenkins_password)
    # Getting Jenkins test job name from configuration
    config = utils.get_configuration()
    jenkins_test_job = config['jenkins_test_job']
    if not server.get_job_name(jenkins_test_job):
        server.create_job(jenkins_test_job, jenkins.EMPTY_CONFIG_XML)
    if server.get_job_name(jenkins_test_job):
        next_build_num = server.get_job_info(jenkins_test_job)['nextBuildNumber']
        # If this is first build number skip building check
        if next_build_num != 1:
            # Check that test job is not running at this moment,
            # Otherwise skip the test
            last_build_num = server.get_job_info(jenkins_test_job)['lastBuild'].get('number')
            last_build_status = server.get_build_info(jenkins_test_job, last_build_num)['building']
            if last_build_status:
                pytest.skip("Test job {0} is already running").format(jenkins_test_job)
        server.build_job(jenkins_test_job)
        timeout = 0
        # Use job status True by default to exclude timeout between build job and start job.
        job_status = True
        while job_status and (timeout < 180):
            time.sleep(10)
            timeout += 10
            job_status = server.get_build_info(jenkins_test_job, next_build_num)['building']
        job_result = server.get_build_info(jenkins_test_job, next_build_num)['result']
    else:
        pytest.skip("The job {0} was not found").format(jenkins_test_job)
    assert job_result == 'SUCCESS', (
        "Test job '{}' build is not successful or timeout is too "
        "small.".format(jenkins_test_job)
    )
