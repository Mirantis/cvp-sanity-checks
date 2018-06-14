import pytest
import json
import os
from cvp_checks import utils
import lxml, requests
from bs4 import BeautifulSoup 


packages = {}

# without SIMPLE_PACKAGES env varibale, we are not going to
# collect versions for packages
if 'SIMPLE_PACKAGES' in os.environ.keys():
    config = utils.get_configuration()
    packages = json.loads(config['simple_packages'][os.environ['SIMPLE_PACKAGES']])
    not_used_packages = json.loads(config['simple_packages'][os.environ['SIMPLE_PACKAGES']])
    try:
        # let's use latest by default
        version = 'latest'
        if os.environ['SIMPLE_PACKAGES'] == 'mitaka':
            # mitaka docs are obsolete, let's use config only
            version = 'q0-17'
        if os.environ['SIMPLE_PACKAGES'] == 'ocata':
            version = 'q4-17'
        if os.environ['SIMPLE_PACKAGES'] == 'pike':
            version = 'q1-18'
        # get page
        page = requests.get("https://docs.mirantis.com/mcp/{}/mcp-release-notes/"
                            "components-versions.html".format(version))

        soup = BeautifulSoup(page.content, 'lxml')
        table = soup.find("table")

        # parse table with versions
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            flag = 0
            comments = ''
            if cells == []:
                continue
            for comp in packages:
                # remove this when document is updated
                if len(cells) > 3:
                    comments = cells[3].text
                cells = [cell.text.replace('<td>_|</td>','').lower() for cell in cells]
                # will be simplified after updating doc
                version = cells[2].replace('x','').strip('.').split(",")[0].split(" ")[0]
                if comp == cells[1] or comp in comments:
                    if packages[comp] != version:
                        print "\nVersion update for {}".format (comp)
                        packages[comp] = version
                    flag = 1
                    if comp in not_used_packages:
                        del not_used_packages[comp]
                    continue
            if flag == 0:
                print "Component/service {0} from site is not found in config".format(cells[1].text)
        print "Packages in config, that are not found on site:"
        print not_used_packages

    except Exception:
        print "\nCannot get info from Mirantis web site!"

print "\nPackages to check on environment"
print packages


def test_simple_packages(local_salt_client):
    if 'SIMPLE_PACKAGES' not in os.environ.keys():
         pytest.skip("This test will be skipped (full package verification will be conducted)")
    packages_exclude = config['exclude_packages']
    active_nodes = utils.get_active_nodes()
    nodes_packages = local_salt_client.cmd(
        utils.list_to_target_string(active_nodes, 'or'),
        'lowpkg.list_pkgs',
        expr_form='compound')
    not_verified = packages.keys()
    pkts_data = []
    for name in packages.keys():
        row = []
        ver = packages[name]
        # iterate by list of nodes
        for node in nodes_packages.keys():
            compare_on_this_node = [pack for pack in nodes_packages[node].keys() if pack not in packages_exclude and name in pack and 'salt-formula-' not in pack]
            if compare_on_this_node:
                # so we have a list of packages, matched by mask and not excluded
                if name in not_verified:
                    not_verified.remove(name)
                for pack in compare_on_this_node:
                    if ver not in nodes_packages[node][pack]:
                        row.append("{0}: Wrong version. Expected {1}={2}, but has {3} for {4}".format(node, name, ver, nodes_packages[node][pack], pack))
        if row != []:
            pkts_data.append(row)
    print "NOT Verified packages"
    print not_verified
    assert len(pkts_data) <= 1, \
        "Several problems found: {0}".format(
        json.dumps(pkts_data, indent=4))
