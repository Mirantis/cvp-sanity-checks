import json
import utils
import pytest


@pytest.mark.sl_dup
# RabbitmqServiceDown, RabbitmqErrorLogsTooHigh
# TODO: a better test
@pytest.mark.full
def test_checking_rabbitmq_cluster(local_salt_client):
    # disable config for this test
    # it may be reintroduced in future
    config = utils.get_configuration()
    # request pillar data from rmq nodes
    # TODO: pillar.get
    rabbitmq_pillar_data = local_salt_client.cmd(
        tgt='rabbitmq:server',
        fun='pillar.get',
        param='rabbitmq:cluster',
        expr_form='pillar')
    if sum([len(v) for v in rabbitmq_pillar_data.values()]) == 0:
        pytest.skip("No RabbitMQ cluster pillar available")
    # creating dictionary {node:cluster_size_for_the_node}
    # with required cluster size for each node
    control_dict = {}
    required_cluster_size_dict = {}

    # check rabbitmq version
    version_data = local_salt_client.cmd(
        tgt='I@rabbitmq:server',
        fun='pkg.version',
        param='rabbitmq-server',
        expr_form='compound'
    )

    rabbitmq_versions = set(version_data.values())

    assert len(rabbitmq_versions) == 1, (
        "Non-matching RabbitMQ versions installed:{}".format(version_data)
    )

    rabbitmq_version = rabbitmq_versions.pop()

    # check if the installed RabbitMQ is 3.8
    newer_rabbit = int(local_salt_client.cmd(
        tgt='I@salt:master',
        fun='pkg.version_cmp',
        param=['{}'.format(rabbitmq_version), '3.8'],
        expr_form='compound'
    ).popitem()[1]) >= 0

    suffix = ' --formatter json' if newer_rabbit else ''
    # request actual data from rmq nodes
    rabbit_actual_data = local_salt_client.cmd(
        tgt='rabbitmq:server',
        param=r'rabbitmqctl cluster_status{} '
              r'| grep "nodes,\|running_nodes"'.format(suffix),
        expr_form='pillar'
    )
    if newer_rabbit:
        temp = {}
        for node in rabbit_actual_data:
            try:
                node_data = json.loads(rabbit_actual_data[node])
                temp[node] = "{}, {}".format(
                    node_data["disk_nodes"], node_data["running_nodes"])
            except json.decoder.JSONDecodeError:
                pass
        rabbit_actual_data = temp

    for node in rabbitmq_pillar_data:
        if node in config.get('skipped_nodes'):
            del rabbit_actual_data[node]
            continue
        cluster_size_from_the_node = len(
            rabbitmq_pillar_data[node]['members'])
        required_cluster_size_dict.update({node: cluster_size_from_the_node})

    # find actual cluster size for each node
    for node in rabbit_actual_data:
        running_nodes_count = 0
        # rabbitmqctl cluster_status output contains
        # 2 * # of nodes 'rabbit@' entries
        running_nodes_count = rabbit_actual_data[node].count('rabbit@') // 2
        # update control dictionary with values
        # {node:actual_cluster_size_for_node}
        if required_cluster_size_dict[node] != running_nodes_count:
            control_dict.update({node: running_nodes_count})

    assert len(control_dict) == 0, (
        "RabbitMQ cluster is probably "
        "broken - the cluster size for each node should be ({}),\nbut the "
        "following nodes have other values:\n{}".format(
            len(list(required_cluster_size_dict.keys())), control_dict)
    )
