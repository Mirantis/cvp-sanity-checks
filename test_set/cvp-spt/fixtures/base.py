import pytest
import utils
import random
import time
from utils import os_client

@pytest.fixture(scope='session')
def local_salt_client():
    return utils.init_salt_client()


# TODO: fix
# should not be executed on any test run
nodes = utils.get_pairs()
hw_nodes = utils.get_hw_pairs()


@pytest.fixture(scope='session', params=nodes.values(), ids=nodes.keys())
def pair(request):
    return request.param


@pytest.fixture(scope='session', params=hw_nodes.values(), ids=hw_nodes.keys())
def hw_pair(request):
    return request.param


@pytest.fixture(scope='session')
def openstack_clients(local_salt_client):
    nodes_info = local_salt_client.cmd(
        'keystone:server', 'pillar.get',
        ['keystone:server'],
        expr_form='pillar')
    if nodes_info.__len__() < 1:
        pytest.skip("No keystone server found")
        return False
    keystone = nodes_info[nodes_info.keys()[0]]
    url = 'http://{ip}:{port}/'.format(ip=keystone['bind']['public_address'],
                                       port=keystone['bind']['public_port'])
    return os_client.OfficialClientManager(
        username=keystone['admin_name'],
        password=keystone['admin_password'],
        tenant_name=keystone['admin_tenant'],
        auth_url=url,
        cert=False,
        domain='Default',
        )


@pytest.fixture(scope='session')
def os_resources(openstack_clients):
    os_actions = os_client.OSCliActions(openstack_clients)
    os_resource = {}
    config = utils.get_configuration()
    image_name = config.get('image_name') or ['Ubuntu']

    os_images_list = [image.id for image in openstack_clients.image.images.list(filters={'name': image_name})]
    if os_images_list.__len__() == 0:
        print "No images with name {}. This name can be redefined with 'image_name' env var ".format(image_name)
        exit()

    os_resource['image_id'] = str(os_images_list[0])

    os_resource['flavor_id'] = [flavor.id for flavor in openstack_clients.compute.flavors.list() if flavor.name == 'spt-test']
    if not os_resource['flavor_id']:
        os_resource['flavor_id'] = os_actions.create_flavor('spt-test', 1536, 1, 3).id
    else:
        os_resource['flavor_id'] = str(os_resource['flavor_id'][0])

    os_resource['sec_group'] = os_actions.create_sec_group()
    os_resource['keypair'] = openstack_clients.compute.keypairs.create('spt-test-{}'.format(random.randrange(100, 999)))
    os_resource['net1'] = os_actions.create_network_resources()
    os_resource['ext_net'] = os_actions.get_external_network()
    adm_tenant = os_actions.get_admin_tenant()
    os_resource['router'] = os_actions.create_router(os_resource['ext_net'], adm_tenant.id)
    os_resource['net2'] = os_actions.create_network(adm_tenant.id)
    os_resource['subnet2'] = os_actions.create_subnet(os_resource['net2'], adm_tenant, '10.2.7.0/24')
    for subnet in openstack_clients.network.list_subnets()['subnets']:
        if subnet['network_id'] == os_resource['net1']['id']:
            os_resource['subnet1'] = subnet['id']

    openstack_clients.network.add_interface_router(os_resource['router']['id'], {'subnet_id': os_resource['subnet1']})
    openstack_clients.network.add_interface_router(os_resource['router']['id'], {'subnet_id': os_resource['subnet2']['id']})
    yield os_resource
    # time.sleep(5)
    openstack_clients.network.remove_interface_router(os_resource['router']['id'], {'subnet_id': os_resource['subnet1']})
    openstack_clients.network.remove_interface_router(os_resource['router']['id'], {'subnet_id': os_resource['subnet2']['id']})
    openstack_clients.network.remove_gateway_router(os_resource['router']['id'])
    time.sleep(5)
    openstack_clients.network.delete_router(os_resource['router']['id'])
    time.sleep(5)
    # openstack_clients.network.delete_subnet(subnet1['id'])
    openstack_clients.network.delete_network(os_resource['net1']['id'])
    openstack_clients.network.delete_network(os_resource['net2']['id'])

    openstack_clients.compute.security_groups.delete(os_resource['sec_group'].id)
    openstack_clients.compute.keypairs.delete(os_resource['keypair'].name)

    openstack_clients.compute.flavors.delete(os_resource['flavor_id'])
