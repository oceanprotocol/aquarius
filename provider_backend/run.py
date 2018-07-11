import os

import sys

from provider_backend.myapp import app
from provider_backend.constants import BaseURLs, DEFAULT_ASSETS_FOLDER


if 'UPLOADS_FOLDER' in os.environ and os.environ['UPLOADS_FOLDER']:
    app.config['UPLOADS_FOLDER'] = os.environ['UPLOADS_FOLDER']
else:
    app.config['UPLOADS_FOLDER'] = DEFAULT_ASSETS_FOLDER

if 'CONFIG_FILE' in os.environ and os.environ['CONFIG_FILE']:
    app.config['CONFIG_FILE'] = os.environ['CONFIG_FILE']
else:
    print('A config file must be set in the environment variable "CONFIG_FILE".')
    sys.exit(1)


from provider_backend.app.assets import assets
app.register_blueprint(assets, url_prefix=BaseURLs.BASE_PROVIDER_URL + '/assets')

if __name__ == '__main__':
    app.run()
