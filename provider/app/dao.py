from oceandb_driver_interface import OceanDb


class Dao(object):

    def __init__(self, config_file):
        self.oceandb = OceanDb(config_file).plugin

    def get_assets(self):
        assets = self.oceandb.list()
        asset_with_id = []
        for asset in assets:
            try:
                asset_with_id.append(self.oceandb.read(asset['data']['resource_id']))
            except Exception as e:
                print(e)
                pass
        return asset_with_id

    def get(self, resource_id):
        return self.oceandb.read(resource_id)

    def register(self, record, resource_id):
        return self.oceandb.write(record, resource_id)
    # def register(self, record):
    #     return self.oceandb.write(record)

    def update(self, record, resource_id):
        return self.oceandb.update(record, resource_id)

    def delete(self, resource_id):
        return self.oceandb.delete(resource_id)
