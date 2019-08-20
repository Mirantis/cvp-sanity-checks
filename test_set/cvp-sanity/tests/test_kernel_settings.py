import pytest
import json


@pytest.mark.xfail(reason='PROD-31892')
def test_sysctl_variables(local_salt_client, nodes_in_group):
    """
    # Request kernel setting from linux:system:kernel:sysctl
    # Request the same setting from sysctl utility on the node
    # Compare that value in sysctl equals to the same value in pillars

    """

    def normalize_value(value_in_string):
        """
        Changes to INT if value_in_string is parcible to int
        Replaces \t with spaces if value_in_string is a string

        :param value_in_string:
        :return:
        """
        if '\t' in value_in_string:
            return value_in_string.replace('\t', ' ')

        try:
            return int(value_in_string)
        except ValueError:
            pass

        return value_in_string

    issues = dict()
    group, nodes = nodes_in_group
    expected_kernel_params_by_nodes = local_salt_client.cmd(
        tgt="L@"+','.join(nodes),
        fun='pillar.get',
        param="linux:system:kernel:sysctl",
        expr_form='compound'
    )

    # Gather all params names from pillars and request their availability
    # To get only specified values from system need to request them in the nex format
    # 'sysctl param1 param2 param3 param4'

    for node in expected_kernel_params_by_nodes.keys():
        actual_kernel_params_for_node = local_salt_client.cmd(
            tgt=node,
            fun='cmd.run',
            param="sysctl {}".format(" ".join(expected_kernel_params_by_nodes[node].keys())),
            expr_form='compound'
        )
        # make transfer string to dict format
        #   it does a magic from
        # "vm.watermark_scale_factor = 10\nvm.zone_reclaim_mode = 0"
        #   to
        # {
        #     "vm.zone_reclaim_mode": "0",
        #     "vm.watermark_scale_factor": "10"
        # }

        values = {param.split(' = ')[0]: normalize_value(param.split(' = ')[-1])
                  for param in actual_kernel_params_for_node[node].split('\n')}

        differences = [ "Parameter '{}' is not set === Expected '{}' === Got in sysctl '{}'".format(key, expected_kernel_params_by_nodes[node].get(key), actual)
                        for key, actual in values.items()
                        if  expected_kernel_params_by_nodes[node].get(key) != actual ]
        if differences.__len__() > 0:
            issues[node] = differences

    assert issues.__len__() == 0, (
        "There are inconsistencies between kernel settings defined in pillars "
        "and actual settings on nodes of '{}' group: {}".format(
            group, json.dumps(issues, indent=4))
    )
