import utils
import pytest


@pytest.mark.sl_dup
#RabbitmqServiceDown, RabbitmqErrorLogsTooHigh
#TODO: a better test
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
    # creating dictionary {node:cluster_size_for_the_node}
    # with required cluster size for each node
    control_dict = {}
    required_cluster_size_dict = {}
    # request actual data from rmq nodes
    rabbit_actual_data = local_salt_client.cmd(
        tgt='rabbitmq:server',
        param='rabbitmqctl cluster_status', expr_form='pillar')
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
        # 3 * # of nodes 'rabbit@' entries + 1
        running_nodes_count = (rabbit_actual_data[node].count('rabbit@') - 1)/3
        # update control dictionary with values
        # {node:actual_cluster_size_for_node}
        if required_cluster_size_dict[node] != running_nodes_count:
            control_dict.update({node: running_nodes_count})

    assert not len(control_dict), (
        "RabbitMQ cluster is probably "
        "broken - the cluster size for each node should be ({}),\nbut the "
        "following nodes have other values:\n{}".format(
            len(required_cluster_size_dict.keys()), control_dict)
    )
