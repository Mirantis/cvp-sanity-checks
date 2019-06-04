import pytest
import json
import utils
import logging

# Some nodes can have services that are not applicable for other nodes in similar group.
# For example , there are 3 node in kvm group, but just kvm03 node has srv-volumes-backup.mount service
# in service.get_all
#                        NODE NAME          SERVICE_NAME
inconsistency_rule = {"kvm03": ["srv-volumes-backup.mount", "rsync"]}


@pytest.mark.full
def test_check_services(local_salt_client, nodes_in_group):
    """
    Skips services if they are not consistent for all node.
    Inconsistent services will be checked with another test case
    """
    exclude_services = utils.get_configuration().get("skipped_services", [])
    services_by_nodes = local_salt_client.cmd(tgt="L@"+','.join(nodes_in_group),
                                              fun='service.get_all',
                                              expr_form='compound')

    if len(services_by_nodes.keys()) < 2:
        pytest.skip("Nothing to compare - only 1 node")

    # PROD-30833
    gtw01 = local_salt_client.pillar_get(
        param='_param:openstack_gateway_node01_hostname') or 'gtw01'
    cluster_domain = local_salt_client.pillar_get(
        param='_param:cluster_domain') or '.local'
    gtw01 += '.' + cluster_domain
    if gtw01 in nodes_in_group:
        octavia = local_salt_client.cmd(tgt="L@" + ','.join(nodes_in_group),
                                        fun='pillar.get',
                                        param='octavia:manager:enabled',
                                        expr_form='compound')
        gtws = [gtw for gtw in octavia.values() if gtw]
        if len(gtws) == 1 and gtw01 in services_by_nodes.keys():
            services_by_nodes.pop(gtw01)
            logging.info("gtw01 node is skipped in test_check_services")

    nodes = []
    pkts_data = []
    all_services = set()

    for node in services_by_nodes:
        if not services_by_nodes[node]:
            # TODO: do not skip node
            logging.info("Node {} is skipped".format (node))
            continue
        nodes.append(node)
        all_services.update(services_by_nodes[node])

    for srv in all_services:
        if srv in exclude_services:
            continue
        service_existence = dict()
        for node in nodes:
            short_name_of_node = node.split('.')[0]
            if inconsistency_rule.get(short_name_of_node) is not None and srv in inconsistency_rule[short_name_of_node]:
                # Skip the checking of some service on the specific node
                break
            elif srv in services_by_nodes[node]:
                # Found service on node
                service_existence[node] = "+"
            else:
                # Not found expected service on node
                service_existence[node] = "No service"
        if set(service_existence.values()).__len__() > 1:
            report = ["{node}: {status}".format(node=node, status=status) for node, status in service_existence.items()]
            report.sort()
            report.insert(0, srv)
            pkts_data.append(report)
    assert len(pkts_data) == 0, \
        "Several problems found: {0}".format(
        json.dumps(pkts_data, indent=4))


# TODO : remake this test to make workable https://mirantis.jira.com/browse/PROD-25958

# def _check_services_on_special_node(local_salt_client, nodes_in_group):
#     """
#     Check that specific node has service.
#     Nodes and proper services should be defined in inconsistency_rule dictionary
#
#     :print: Table with nodes which don't have required services and not existed services
#     """
#
#     output = local_salt_client.cmd("L@" + ','.join(nodes_in_group), 'service.get_all', expr_form='compound')
#     if len(output.keys()) < 2:
#         pytest.skip("Nothing to compare - just 1 node")
#
#     def is_proper_service_for_node(_service, _node):
#         """
#         Return True if service exists on node and exists in inconsistency_rule
#         Return True if service doesn't exists on node and doesn't exists in inconsistency_rule
#         Return False otherwise
#         :param _service: string
#         :param _node: string full name of node
#         :return: bool, read description for further details
#         """
#         short_name_of_node = _node.split('.')[0]
#         if short_name_of_node not in inconsistency_rule.keys():
#             return False
#
#         if _service in inconsistency_rule[short_name_of_node] and \
#                 _service in output[_node]:
#             # Return True if service exists on node and exists in inconsistency_rule
#             return True
#
#         if _service not in inconsistency_rule[short_name_of_node] and \
#                 _service not in output[_node]:
#             # Return True if service exists on node and exists in inconsistency_rule
#             return True
#         print("return False for {} in {}".format(_service, _node))
#         # error_text = ""
#         return False
#
#     errors = list()
#     for node, expected_services in inconsistency_rule.items():
#         print("Check {} , {} ".format(node, expected_services))
#         # Skip if there is no proper node. Find nodes that contains node_title (like 'kvm03') in their titles
#         if not any([node in node_name for node_name in output.keys()]):
#             continue
#         for expected_service in expected_services:
#             service_on_nodes = {_node: expected_service if expected_service in _service else None
#                                 for _node, _service
#                                 in output.items()}
#             print([is_proper_service_for_node(expected_service, _node)
#                   for _node
#                   in output.keys()])
#             if not all([is_proper_service_for_node(expected_service, _node)
#                         for _node
#                         in output.keys()]):
#                 errors.append(service_on_nodes)
#
#     assert errors.__len__() == 0, json.dumps(errors, indent=4)
#     assert False
