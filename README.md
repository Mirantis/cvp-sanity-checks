MCP sanity checks
========================

This is salt-based set of tests for basic verification of MCP deployments

How to start
=======================

1) Clone repo to any node (node must have an access via http to salt master):
```bash
   # root@cfg-01:~/# git clone https://github.com/Mirantis/cvp-sanity-checks
   # cd cvp-sanity-checks
```
Use git config --global http.proxy http://proxyuser:proxypwd@proxy.server.com:8080
if needed.

2) Install virtualenv
```bash
   # curl -O https://pypi.python.org/packages/source/v/virtualenv/virtualenv-X.X.tar.gz
   # tar xvfz virtualenv-X.X.tar.gz
   # cd virtualenv-X.X
   # sudo python setup.py install
```
or
1```bash
   # apt-get install python-virtualenv
```

3) Create virtualenv and install requirements and package:

```bash
   # virtualenv --system-site-packages .venv
   # source .venv/bin/activate
   # pip install --proxy http://$PROXY:8678 -r requirements.txt
   # python setup.py install
   # python setup.py develop
```

4) Configure:
```bash
   # vim cvp_checks/global_config.yaml
```
SALT credentials are mandatory for tests.


Other settings are optional (please keep uncommented with default values)


Alternatively, you can specify these settings via env variables:
```bash
export SALT_URL=http://10.0.0.1:6969
```
For array-type settings please do:
```bash
export skipped_nodes='ctl01.example.com,ctl02.example.com'
```

5) Start tests:
```bash
   # pytest --tb=short -sv cvp_checks/tests/
```
or
```bash
   # pytest -sv cvp_checks/tests/ --ignore cvp_checks/tests/test_mtu.py
```
