from flask import Flask
from provider_backend.app.assets import assets
from provider_backend.constants import BaseURLs

app = Flask(__name__)
app.register_blueprint(assets, url_prefix=BaseURLs.BASE_PROVIDER_URL + '/assets')

if __name__ == '__main__':
    app.run()
