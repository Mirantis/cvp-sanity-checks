import jenkins
from xml.dom import minidom
import utils
import json
import pytest
import time
import os
from pygerrit2 import GerritRestAPI, HTTPBasicAuth
from requests import HTTPError
import git
import ldap
import ldap.modlist as modlist
import logging

def join_to_gerrit(local_salt_client, gerrit_user, gerrit_password):
    gerrit_port = local_salt_client.pillar_get(
        tgt='I@gerrit:client and not I@salt:master',
        param='_param:haproxy_gerrit_bind_port',
        expr_form='compound')
    gerrit_address = local_salt_client.pillar_get(
        tgt='I@gerrit:client and not I@salt:master',
        param='_param:haproxy_gerrit_bind_host',
        expr_form='compound')
    url = 'http://{0}:{1}'.format(gerrit_address,gerrit_port)
    auth = HTTPBasicAuth(gerrit_user, gerrit_password)
    rest = GerritRestAPI(url=url, auth=auth)
    return rest


def join_to_jenkins(local_salt_client, jenkins_user, jenkins_password):
    jenkins_port = local_salt_client.pillar_get(
        tgt='I@jenkins:client and not I@salt:master',
        param='_param:haproxy_jenkins_bind_port',
        expr_form='compound')
    jenkins_address = local_salt_client.pillar_get(
        tgt='I@jenkins:client and not I@salt:master',
        param='_param:haproxy_jenkins_bind_host',
        expr_form='compound')
    jenkins_url = 'http://{0}:{1}'.format(jenkins_address,jenkins_port)
    server = jenkins.Jenkins(jenkins_url, username=jenkins_user, password=jenkins_password)
    return server


def get_password(local_salt_client,service):
    password = local_salt_client.pillar_get(
        tgt=service,
        param='_param:openldap_admin_password')
    return password


@pytest.mark.full
def test_drivetrain_gerrit(local_salt_client, check_cicd):
    gerrit_password = get_password(local_salt_client,'gerrit:client')
    gerrit_error = ''
    current_date = time.strftime("%Y%m%d-%H.%M.%S", time.localtime())
    test_proj_name = "test-dt-{0}".format(current_date)
    gerrit_port = local_salt_client.pillar_get(
        tgt='I@gerrit:client and not I@salt:master',
        param='_param:haproxy_gerrit_bind_port',
        expr_form='compound')
    gerrit_address = local_salt_client.pillar_get(
        tgt='I@gerrit:client and not I@salt:master',
        param='_param:haproxy_gerrit_bind_host',
        expr_form='compound')
    try:
        #Connecting to gerrit and check connection
        server = join_to_gerrit(local_salt_client,'admin',gerrit_password)
        gerrit_check = server.get("/changes/?q=owner:self%20status:open")
        #Check deleteproject plugin and skip test if the plugin is not installed
        gerrit_plugins = server.get("/plugins/?all")
        if 'deleteproject' not in gerrit_plugins:
            pytest.skip("Delete-project plugin is not installed")
        #Create test project and add description
        server.put("/projects/"+test_proj_name)
        server.put("/projects/"+test_proj_name+"/description",json={"description":"Test DriveTrain project","commit_message": "Update the project description"})
    except HTTPError as e:
        gerrit_error = e
    try:
        #Create test folder and init git
        repo_dir = os.path.join(os.getcwd(),test_proj_name)
        file_name = os.path.join(repo_dir, current_date)
        repo = git.Repo.init(repo_dir)
        #Add remote url for this git repo
        origin = repo.create_remote('origin', 'http://admin:{1}@{2}:{3}/{0}.git'.format(test_proj_name,gerrit_password,gerrit_address,gerrit_port))
        #Add commit-msg hook to automatically add Change-Id to our commit
        os.system("curl -Lo {0}/.git/hooks/commit-msg 'http://admin:{1}@{2}:{3}/tools/hooks/commit-msg' > /dev/null 2>&1".format(repo_dir,gerrit_password,gerrit_address,gerrit_port))
        os.system("chmod u+x {0}/.git/hooks/commit-msg".format(repo_dir))
        #Create a test file
        f = open(file_name, 'w+')
        f.write("This is a test file for DriveTrain test")
        f.close()
        #Add file to git and commit it to Gerrit for review
        repo.index.add([file_name])
        repo.index.commit("This is a test commit for DriveTrain test")
        repo.git.push("origin", "HEAD:refs/for/master")
        #Get change id from Gerrit. Set Code-Review +2 and submit this change
        changes = server.get("/changes/?q=project:{0}".format(test_proj_name))
        last_change = changes[0].get('change_id')
        server.post("/changes/{0}/revisions/1/review".format(last_change),json={"message": "All is good","labels":{"Code-Review":"+2"}})
        server.post("/changes/{0}/submit".format(last_change))
    except HTTPError as e:
        gerrit_error = e
    finally:
        #Delete test project
        server.post("/projects/"+test_proj_name+"/deleteproject~delete")
    assert gerrit_error == '',\
        'Something is wrong with Gerrit'.format(gerrit_error)


@pytest.mark.full
def test_drivetrain_openldap(local_salt_client, check_cicd):
    """
         1. Create a test user 'DT_test_user' in openldap
         2. Add the user to admin group
         3. Login using the user to Jenkins
         4. Check that no error occurred
         5. Add the user to devops group in Gerrit and then login to Gerrit
        using test_user credentials.
         6 Start job in jenkins from this user
         7. Get info from gerrit  from this user
         6. Finally, delete the user from admin
        group and openldap
    """

    # TODO split to several test cases. One check - per one test method. Make the login process in fixture
    ldap_password = get_password(local_salt_client,'openldap:client')
    #Check that ldap_password is exists, otherwise skip test
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
    ldap_con_admin = local_salt_client.pillar_get(
        tgt='openldap:client',
        param='openldap:client:server:auth:user')
    ldap_url = 'ldap://{0}:{1}'.format(ldap_address,ldap_port)
    ldap_error = ''
    ldap_result = ''
    gerrit_result = ''
    gerrit_error = ''
    jenkins_error = ''
    #Test user's CN
    test_user_name = 'DT_test_user'
    test_user = 'cn={0},ou=people,{1}'.format(test_user_name,ldap_dc)
    #Admins group CN
    admin_gr_dn = 'cn=admins,ou=groups,{0}'.format(ldap_dc)
    #List of attributes for test user
    attrs = {}
    attrs['objectclass'] = ['organizationalRole', 'simpleSecurityObject', 'shadowAccount']
    attrs['cn'] = test_user_name
    attrs['uid'] = test_user_name
    attrs['userPassword'] = 'aSecretPassw'
    attrs['description'] = 'Test user for CVP DT test'
    searchFilter = 'cn={0}'.format(test_user_name)
    #Get a test job name from config
    config = utils.get_configuration()
    jenkins_cvp_job = config['jenkins_cvp_job']
    #Open connection to ldap and creating test user in admins group
    try:
        ldap_server = ldap.initialize(ldap_url)
        ldap_server.simple_bind_s(ldap_con_admin,ldap_password)
        ldif = modlist.addModlist(attrs)
        ldap_server.add_s(test_user,ldif)
        ldap_server.modify_s(admin_gr_dn,[(ldap.MOD_ADD, 'memberUid', [test_user_name],)],)
        #Check search test user in LDAP
        searchScope = ldap.SCOPE_SUBTREE
        ldap_result = ldap_server.search_s(ldap_dc, searchScope, searchFilter)
    except ldap.LDAPError as e:
        ldap_error = e
    try:
        #Check connection between Jenkins and LDAP
        jenkins_server = join_to_jenkins(local_salt_client,test_user_name,'aSecretPassw')
        jenkins_version = jenkins_server.get_job_name(jenkins_cvp_job)
        #Check connection between Gerrit and LDAP
        gerrit_server = join_to_gerrit(local_salt_client,'admin',ldap_password)
        gerrit_check = gerrit_server.get("/changes/?q=owner:self%20status:open")
        #Add test user to devops-contrib group in Gerrit and check login
        _link = "/groups/devops-contrib/members/{0}".format(test_user_name)
        gerrit_add_user = gerrit_server.put(_link)
        gerrit_server = join_to_gerrit(local_salt_client,test_user_name,'aSecretPassw')
        gerrit_result = gerrit_server.get("/changes/?q=owner:self%20status:open")
    except HTTPError as e:
        gerrit_error = e
    except jenkins.JenkinsException as e:
        jenkins_error = e
    finally:
        ldap_server.modify_s(admin_gr_dn,[(ldap.MOD_DELETE, 'memberUid', [test_user_name],)],)
        ldap_server.delete_s(test_user)
        ldap_server.unbind_s()
    assert ldap_error == '', \
        '''Something is wrong with connection to LDAP:
            {0}'''.format(e)
    assert jenkins_error == '', \
        '''Connection to Jenkins was not established:
            {0}'''.format(e)
    assert gerrit_error == '', \
        '''Connection to Gerrit was not established:
            {0}'''.format(e)
    assert ldap_result !=[], \
        '''Test user was not found'''


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
        for line in docker_services_by_nodes[docker_services_by_nodes.keys()[0]].split('\n'):
            if line[line.find('/') - 1] != line[line.find('/') + 1] \
               and 'replicated' in line:
                wrong_items.append(line)
        if len(wrong_items) == 0:
            break
        else:
            logging.error('''Some DriveTrain services doesn't have expected number of replicas:
                  {}\n'''.format(json.dumps(wrong_items, indent=4)))
            time.sleep(5)
    assert len(wrong_items) == 0


@pytest.mark.full
def test_drivetrain_components_and_versions(local_salt_client, check_cicd):
    """
        1. Execute command `docker service ls --format "{{.Image}}"'` on  the 'I@gerrit:client' target
        2. Execute  ` salt -C 'I@gerrit:client' pillar.get docker:client:images`
        3. Check that list of images from step 1 is the same as a list from the step2
        4. Check that all docker services has label that equals to mcp_version

    """
    config = utils.get_configuration()
    if not config['drivetrain_version']:
        expected_version = \
            local_salt_client.pillar_get(param='_param:mcp_version') or \
            local_salt_client.pillar_get(param='_param:apt_mk_version')
        if not expected_version:
            pytest.skip("drivetrain_version is not defined. Skipping")
    else:
        expected_version = config['drivetrain_version']
    table_with_docker_services = local_salt_client.cmd(tgt='I@gerrit:client',
                                                       param='docker service ls --format "{{.Image}}"',
                                                       expr_form='compound')
    expected_images = local_salt_client.pillar_get(tgt='gerrit:client',
                                                   param='docker:client:images')
    mismatch = {}
    actual_images = {}
    for image in set(table_with_docker_services[table_with_docker_services.keys()[0]].split('\n')):
        actual_images[image.split(":")[0]] = image.split(":")[-1]
    for image in set(expected_images):
        im_name = image.split(":")[0]
        if im_name not in actual_images:
            mismatch[im_name] = 'not found on env'
        elif image.split(":")[-1] != actual_images[im_name]:
            mismatch[im_name] = 'has {actual} version instead of {expected}'.format(
                actual=actual_images[im_name], expected=image.split(":")[-1])
    assert len(mismatch) == 0, \
        '''Some DriveTrain components do not have expected versions:
              {}'''.format(json.dumps(mismatch, indent=4))


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
        if actual_version not in expected_version and expected_version != '':
            version_mismatch.append("Job {0} has {1} branch."
                                    "Expected {2}".format(job_name,
                                                          actual_version,
                                                          expected_version))
    assert len(version_mismatch) == 0, \
        '''Some DriveTrain jobs have version/branch mismatch:
              {}'''.format(json.dumps(version_mismatch, indent=4))


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
    assert job_result == 'SUCCESS', \
        '''Test job '{0}' build was not successful or timeout is too small
         '''.format(jenkins_test_job)


@pytest.mark.smoke
# ??
def test_kdt_all_pods_are_available(local_salt_client, check_kdt):
    """
     # Run kubectl get pods -n drivetrain on kdt-nodes to get status for each pod
     # Check that each pod has fulfilled status in the READY column

    """
    pods_statuses_output = local_salt_client.cmd_any(
        tgt='L@'+','.join(check_kdt),
        param='kubectl get pods -n drivetrain |  awk {\'print $1"; "$2\'} | column -t',
        expr_form='compound')

    assert pods_statuses_output != "/bin/sh: 1: kubectl: not found", \
        "Nodes {} don't have kubectl".format(check_kdt)
    # Convert string to list and remove first row with column names
    pods_statuses = pods_statuses_output.split('\n')
    pods_statuses = pods_statuses[1:]

    report_with_errors = ""
    for pod_status in pods_statuses:
        pod, status = pod_status.split('; ')
        actual_replica, expected_replica = status.split('/')

        if actual_replica.strip() != expected_replica.strip():
            report_with_errors += "Pod [{pod}] doesn't have all containers. Expected {expected} containers, actual {actual}\n".format(
                pod=pod,
                expected=expected_replica,
                actual=actual_replica
            )
    assert report_with_errors == "", \
        "\n{sep}{kubectl_output}{sep} \n\n {report} ".format(
            sep="\n" + "-"*20 + "\n",
            kubectl_output=pods_statuses_output,
            report=report_with_errors
        )

@pytest.mark.smoke
# ??
def test_kfg_all_pods_are_available(local_salt_client, check_kfg):
    """
     # Run kubectl get pods -n drivetrain on cfg node to get status for each pod
     # Check that each pod has fulfilled status in the READY column

    """
    # TODO collapse similar tests into one to check pods and add new fixture
    pods_statuses_output = local_salt_client.cmd_any(
        tgt='L@' + ','.join(check_kfg),
        param='kubectl get pods -n drivetrain |  awk {\'print $1"; "$2\'} | column -t',
        expr_form='compound')
    # Convert string to list and remove first row with column names
    pods_statuses = pods_statuses_output.split('\n')
    pods_statuses = pods_statuses[1:]

    report_with_errors = ""
    for pod_status in pods_statuses:
        pod, status = pod_status.split('; ')
        actual_replica, expected_replica = status.split('/')

        if actual_replica.strip() == expected_replica.strip():
            report_with_errors += "Pod [{pod}] doesn't have all containers. Expected {expected} containers, actual {actual}\n".format(
                pod=pod,
                expected=expected_replica,
                actual=actual_replica
            )
    assert report_with_errors != "", \
        "\n{sep}{kubectl_output}{sep} \n\n {report} ".format(
            sep="\n" + "-" * 20 + "\n",
            kubectl_output=pods_statuses_output,
            report=report_with_errors
        )