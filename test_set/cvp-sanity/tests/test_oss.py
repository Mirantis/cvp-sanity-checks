import requests
import csv
import json


def test_oss_status(local_salt_client):
    HAPROXY_STATS_IP = local_salt_client.pillar_get(
        tgt='docker:swarm:role:master',
        param='haproxy:proxy:listen:stats:binds:address')
    proxies = {"http": None, "https": None}
    csv_result = requests.get('http://{}:9600/haproxy?stats;csv"'.format(
                              HAPROXY_STATS_IP),
                              proxies=proxies).content
    data = csv_result.lstrip('# ')
    wrong_data = []
    list_of_services = ['aptly', 'openldap', 'gerrit', 'jenkins', 'postgresql',
                        'pushkin', 'rundeck', 'elasticsearch']
    for service in list_of_services:
        check = local_salt_client.test_ping(tgt='{}:client'.format(service))
        if check:
            lines = [row for row in csv.DictReader(data.splitlines())
                     if service in row['pxname']]
            for row in lines:
                info = "Service {0} with svname {1} and status {2}".format(
                    row['pxname'], row['svname'], row['status'])
                if row['svname'] == 'FRONTEND' and row['status'] != 'OPEN':
                        wrong_data.append(info)
                if row['svname'] != 'FRONTEND' and row['status'] != 'UP':
                        wrong_data.append(info)

    assert len(wrong_data) == 0, \
        '''Some haproxy services are in wrong state
              {}'''.format(json.dumps(wrong_data, indent=4))
