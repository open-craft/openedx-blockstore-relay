Blockstore Relay for Open edX
=============================

|pypi-badge| |travis-badge| |codecov-badge| |doc-badge| |pyversions-badge|
|license-badge|

An Open edX Django plugin application for transferring data between Open edX and `Blockstore
<https://github.com/open-craft/blockstore/>`_.

The current version provides a management command which transfers a Unit (vertical) to a Blockstore Bundle.

Setup Instructions
------------------

On Open edX Devstack:

1. Clone this repo into your devstack's ``src`` folder::

    git clone git@github.com:open-craft/openedx-blockstore-relay.git

2. Install it into Studio's devstack python environment::

    make studio-shell
    pip install -e /edx/src/openedx-blockstore-relay/
    
3. Confirm that the Studio docker container can connect to blockstore (run this from the Studio shell)::

     curl edx.devstack.blockstore:18250/api/v1/ -v

   If it doesn't work, check the Blockstore readme for setup instructions.

4. On your host machine, create/edit `edx-platform/cms/envs/private.py` and add::

    BLOCKSTORE_API_URL = "http://edx.devstack.blockstore:18250/api/v1/"

Usage Instructions
------------------

Any commands shown in this section should be run from the Studio docker shell (``make studio-shell``).

1. Create a collection to hold the content you wish to import::

     curl -d '{"title": "XBlock Collection"}' -H "Content-Type: application/json" -X POST http://edx.devstack.blockstore:18250/api/v1/collections/

   Note the UUID of the new collection.

2. To upload a unit into blockstore, use the management command like this::

    ./manage.py cms transfer_to_blockstore --settings=devstack_docker --verbosity=2 \
    --block-key "block-v1:edX+DemoX+Demo_Course+type@vertical+block@256f17a44983429fb1a60802203ee4e0" \
    --collection-uuid "cccccccc-cccc-cccc-cccc-cccccccccccc"

3. Go to http://localhost:18250/api/v1/bundles/ in a browser to see the newly created bundle.

License
-------

The code in this repository is licensed under the AGPL 3.0 unless otherwise noted.

Please see ``LICENSE.txt`` for details.

How To Contribute
-----------------

Contributions are very welcome.

Please read `How To Contribute <https://github.com/edx/edx-platform/blob/master/CONTRIBUTING.rst>`_ for details.

Even though they were written with ``edx-platform`` in mind, the guidelines
should be followed for Open edX code in general.

PR description template should be automatically applied if you are sending PR from github interface; otherwise you
can find it it at `PULL_REQUEST_TEMPLATE.md <https://github.com/edx/openedx-blockstore-relay/blob/master/.github/PULL_REQUEST_TEMPLATE.md>`_

Issue report template should be automatically applied if you are sending it from github UI as well; otherwise you
can find it at `ISSUE_TEMPLATE.md <https://github.com/edx/openedx-blockstore-relay/blob/master/.github/ISSUE_TEMPLATE.md>`_

Reporting Security Issues
-------------------------

Please do not report security issues in public. Please email security@edx.org.

Getting Help
------------

Have a question about this repository, or about Open edX in general?  Please
refer to this `list of resources`_ if you need any assistance.

.. _list of resources: https://open.edx.org/getting-help


.. |pypi-badge| image:: https://img.shields.io/pypi/v/openedx-blockstore-relay.svg
    :target: https://pypi.python.org/pypi/openedx-blockstore-relay/
    :alt: PyPI

.. |travis-badge| image:: https://travis-ci.org/edx/openedx-blockstore-relay.svg?branch=master
    :target: https://travis-ci.org/open-craft/openedx-blockstore-relay
    :alt: Travis

.. |codecov-badge| image:: http://codecov.io/github/edx/openedx-blockstore-relay/coverage.svg?branch=master
    :target: http://codecov.io/github/edx/openedx-blockstore-relay?branch=master
    :alt: Codecov

.. |doc-badge| image:: https://readthedocs.org/projects/openedx-blockstore-relay/badge/?version=latest
    :target: http://openedx-blockstore-relay.readthedocs.io/en/latest/
    :alt: Documentation

.. |pyversions-badge| image:: https://img.shields.io/pypi/pyversions/openedx-blockstore-relay.svg
    :target: https://pypi.python.org/pypi/openedx-blockstore-relay/
    :alt: Supported Python versions

.. |license-badge| image:: https://img.shields.io/github/license/open-craft/openedx-blockstore-relay.svg
    :target: https://github.com/open-craft/openedx-blockstore-relay/blob/master/LICENSE.txt
    :alt: License
