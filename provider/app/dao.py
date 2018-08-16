from oceandb_driver_interface import OceanDb


class Dao(object):

    def __init__(self, config_file):
        self.oceandb = OceanDb(config_file).plugin

    def get_assets(self):
        assets = self.oceandb.list()
        asset_with_id = []
        for asset in assets:
            try:
                asset_with_id.append(self.oceandb.read(asset['id']))
            except Exception as e:
                print(e)
                pass
        return asset_with_id

    def get(self, asset_id):
        tx_id = self._find_tx_id(asset_id)
        return self.oceandb.read(tx_id)

    def register(self, record):
        return self.oceandb.write(record)

    def update(self, record, asset_id):
        tx_id = self._find_tx_id(asset_id)
        return self.oceandb.update(record, tx_id)

    def delete(self, asset_id):
        tx_id = self._find_tx_id(asset_id)
        return self.oceandb.delete(tx_id)

    def _find_tx_id(self, asset_id):
        all = self.oceandb.list()
        for a in all:
            if a['data']['data']['assetId'] == asset_id:
                return a['id']
            else:
                pass
        return "%s not found" % asset_id
