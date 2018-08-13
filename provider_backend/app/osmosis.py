from datetime import datetime, timedelta
from azure.storage.blob import BlockBlobService
from azure.storage.blob import BlobPermissions


def generate_sasurl(url, account_name, account_key, container):
    bs = BlockBlobService(account_name=account_name,
                          account_key=account_key)
    sas_token = bs.generate_blob_shared_access_signature(container,
                                                         url.split('/')[-1],
                                                         permission=BlobPermissions.READ,
                                                         expiry=datetime.utcnow() + timedelta(hours=24),
                                                         )
    source_blob_url = bs.make_blob_url(container, url.split('/')[-1],
                                       sas_token=sas_token)
    return source_blob_url
