import os
import io


from database.instance import get_oceandb_instance, sanitize_record

get_oceandb_instance(database_name='ocean_test',
                      config_file=os.path.join("..", "/test-config.json"))

import app
app = app.app


def insert_boundary(boundary, buff, at_end=False):
    buff.write(b'--')
    buff.write(boundary.encode())
    if at_end:
        buff.write(b'--\r\n')
    else:
        buff.write(b'\r\n')


def create_file_request_data_and_headers(data, fieldname, filename, content_type):
    boundry = '----WebKitFormBoundary1modcYGLAATJpapo8jhD4UwHbF5asu4u'
    buff = io.BytesIO()

    insert_boundary(boundry, buff)
    buff.write(('Content-Disposition: form-data; name="%s"; filename="%s"' %
                (fieldname, filename)).encode())
    buff.write(b'\r\n')
    buff.write(('Content-Type: %s' % content_type).encode())
    buff.write(b'\r\n')
    buff.write(b'\r\n')
    buff.write(data)
    buff.write(b'\r\n')

    insert_boundary(boundry, buff, at_end=True)

    headers = dict()
    headers['content-type'] = 'multipart/form-data; boundary=%s' % boundry
    headers['Content-Length'] = str(buff.tell())

    return buff.getvalue(), headers


class TestAssets(object):

    def test_get_asset(self, database_instance):
        pass