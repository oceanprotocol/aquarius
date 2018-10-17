from provider.myapp import app
from provider.app.assets import assets
from flask_swagger import swagger
from flask_swagger_ui import get_swaggerui_blueprint
from flask import jsonify
# from squid_py.config_parser import load_config_section
from squid_py.config import Config
from provider.constants import BaseURLs


@app.route("/spec")
def spec():
    swag = swagger(app)
    swag['info']['version'] = "1.0"
    swag['info']['title'] = "Ocean-provider"
    return jsonify(swag)


config = Config(filename=app.config['CONFIG_FILE'])
provider_url = config.provider_url
# Call factory function to create our blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    BaseURLs.SWAGGER_URL,
    provider_url + '/spec',
    config={  # Swagger UI config overrides
        'app_name': "Test application"
    },
)

# Register blueprint at URL
app.register_blueprint(swaggerui_blueprint, url_prefix=BaseURLs.SWAGGER_URL)
app.register_blueprint(assets, url_prefix=BaseURLs.ASSETS_URL)

if __name__ == '__main__':
    app.run()
