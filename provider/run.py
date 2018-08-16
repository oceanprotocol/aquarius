import os

import sys

from provider.myapp import app
from provider.constants import BaseURLs, DEFAULT_ASSETS_FOLDER, DEFAULT_HOST, DEFAULT_PORT

if 'UPLOADS_FOLDER' in os.environ and os.environ['UPLOADS_FOLDER']:
    app.config['UPLOADS_FOLDER'] = os.environ['UPLOADS_FOLDER']
else:
    app.config['UPLOADS_FOLDER'] = DEFAULT_ASSETS_FOLDER

if 'CONFIG_FILE' in os.environ and os.environ['CONFIG_FILE']:
    app.config['CONFIG_FILE'] = os.environ['CONFIG_FILE']
else:
    print('A config file must be set in the environment variable "CONFIG_FILE".')
    sys.exit(1)
if 'HOST' in os.environ and os.environ['HOST']:
    app.config['HOST'] = os.environ['HOST']
else:
    app.config['HOST'] = DEFAULT_HOST
if 'PORT' in os.environ and os.environ['PORT']:
    app.config['PORT'] = os.environ['PORT']
else:
    app.config['PORT'] = DEFAULT_PORT

from provider.app.assets import assets
app.register_blueprint(assets, url_prefix=BaseURLs.ASSETS_URL)

if __name__ == '__main__':
    app.run(host=app.config.get('HOST'),
            port=app.config.get('PORT'))
