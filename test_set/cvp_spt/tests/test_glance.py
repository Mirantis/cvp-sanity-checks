import pytest
import time
import subprocess
import cvp_spt.utils as utils


@pytest.fixture
def create_image():
    line = 'echo "Executing dd on $(hostname -f)"; ' \
           'dd if=/dev/zero of=/tmp/image_mk_framework.dd bs=1M count=9000 ;' \
           'echo "Free space :" ; ' \
           'df -H / '

    subprocess.call(line.split())
    yield
    # teardown
    subprocess.call('rm /tmp/image_mk_framework.dd'.split())
    subprocess.call('rm /tmp/image_mk_framework.download'.split())


def test_speed_glance(create_image, openstack_clients, record_property):
    """
    Simplified Performance Tests Download / upload lance
    1. Step download image
    2. Step upload image
    """
    image = openstack_clients.image.images.create(
        name="test_image",
        disk_format='iso',
        container_format='bare')

    start_time = time.time()
    openstack_clients.image.images.upload(
        image.id,
        image_data=open("/tmp/image_mk_framework.dd", 'rb'))
    end_time = time.time()

    speed_upload = 9000 / (end_time - start_time)

    start_time = time.time()
    with open("/tmp/image_mk_framework.download", 'wb') as image_file:
        for item in openstack_clients.image.images.data(image.id):
            image_file.write(item)
    end_time = time.time()

    speed_download = 9000 / (end_time - start_time)

    openstack_clients.image.images.delete(image.id)
    record_property("Upload", speed_upload)
    record_property("Download", speed_download)

    print "++++++++++++++++++++++++++++++++++++++++"
    print 'upload - {} Mb/s'.format(speed_upload)
    print 'download - {} Mb/s'.format(speed_download)
