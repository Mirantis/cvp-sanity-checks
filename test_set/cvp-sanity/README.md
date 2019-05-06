MCP sanity checks
========================

This is salt-based set of tests for basic verification of MCP deployments

How to start
---
*Target: test engineers*

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
```bash
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
   # vim cvp-sanity/global_config.yaml
```
SALT credentials are mandatory for tests.


Other settings are optional (please keep uncommented with default values)


Alternatively, you can specify these settings via env variables:
```bash
export SALT_URL=http://10.0.0.1:6969
```
For array-type settings please do:
```bash
export skipped_nodes=ctl01.example.com,ctl02.example.com
```

5) Start tests:
```bash
   # pytest --tb=short -sv cvp-sanity/tests/
```
or
```bash
   # pytest -sv cvp-sanity/tests/ --ignore cvp-sanity/tests/test_mtu.py
```

CVP-sanity-checks supports tags (labels/marks/sets). As of now we have smoke,
full and sl_dup sets. Smoke will run essential tests only, full set runs all
tests and sl_dup is a special set that collects the tests that already exist in
Stacklight. Please do not forget to mark your test when you add it.
Example (run smoke tests only):
```bash
   # pytest -v -m smoke
```

Logging
---
*Target: test developers*

To make a logging in the cvp-sanity-tests module more consistent you should follow next recommendations:
+ Do not use **print** methods

+ Each string that needs to be in the stdout should be called with logging.warning level and higher
```python
import logging

def test_t1():
    logging.warning("Alert: Houston we have a problem!")
    logging.error("We've lost a booster!")
    logging.critical("Everything is broken!")
```
So these messages will be displayed in the pytest output after failed tests

+ Use  logging.info and logging.debug to log some trivial string. E.g saving requests/responses, saving states os some variables 
```python
import logging

def test_t2():
    logging.info("Skip {node} in this test")
    logging.debug("Some function is called")
```
These messages will be logged in the log file only. You can forcely enable logging in the sdtout by calling pytest with next parameter
```bash
pytest --log-level=DEBUG
```

Logging to file
---

By default full.log is located in the working directory.
And you can define folder for logs to store by the PYTEST_REPORT_DIR environment variable

List of available environment variables
===
todo