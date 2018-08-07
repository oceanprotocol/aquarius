import os

import sys

from provider_backend.myapp import app
from provider_backend.constants import BaseURLs, DEFAULT_ASSETS_FOLDER
from provider_backend.blockchain.OceanContractsWrapper import OceanContractsWrapper
from provider_backend.blockchain.constants import OceanContracts
from provider_backend.config_parser import load_config_section
from provider_backend.constants import ConfigSections



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
    app.run(host='0.0.0.0', port=5000)
    config_file = app.config['CONFIG_FILE']
    keeper_config = load_config_section(config_file, ConfigSections.KEEPER_CONTRACTS)

    ocean = OceanContractsWrapper(keeper_config['keeper.host'], keeper_config['keeper.port'])
    ocean.init_contracts()
    acl_concise = ocean.contracts[OceanContracts.OCEAN_ACL_CONTRACT][0]
    acl = ocean.contracts[OceanContracts.OCEAN_ACL_CONTRACT][1]
    market_concise = ocean.contracts[OceanContracts.OCEAN_MARKET_CONTRACT][0]
    market = ocean.contracts[OceanContracts.OCEAN_MARKET_CONTRACT][1]
    token = ocean.contracts[OceanContracts.OCEAN_TOKEN_CONTRACT][0]

    provider_account=keeper_config['provider.address']
    print("deploying filters")
    filter_access_consent = ocean.watch_event(OceanContracts.OACL, 'AccessConsentRequested',
                                              ocean.commit_access_request, 250,
                                              fromBlock='latest', filters={"address": provider_account})
    filter_payment = ocean.watch_event(OceanContracts.OMKT, 'PaymentReceived', ocean.publish_encrypted_token, 2500,
                                       fromBlock='latest', filters={"address": provider_account})
    print("Filters deployed")

