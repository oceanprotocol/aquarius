import jwt as jwt
import datetime
from OpenSSL import crypto
from azure.storage.blob import BlobService
from azure.storage import AccessPolicy, SharedAccessPolicy
from collections import namedtuple

from ecies.utils import generate_eth_key
from ecies import encrypt, decrypt

CryptoKeypair = namedtuple('CryptoKeypair', ('private_key', 'public_key'))


def generate_encryption_keys():
    k = generate_eth_key()
    prvhex = k.to_hex()
    pubhex = k.public_key.to_hex()
    return CryptoKeypair(prvhex, pubhex)


def generate_encoding_pair():
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 1024)
    return CryptoKeypair(crypto.dump_privatekey(crypto.FILETYPE_PEM, k),
                         crypto.dump_publickey(crypto.FILETYPE_PEM, k))


def encode(data, secret):
    return jwt.encode(data, secret, algorithm='RS256')


def decode(encoded, secret):
    return jwt.decode(encoded, secret, algorithms='RS256')


def enc(data, publicKey):
    return encrypt(publicKey, data)


def dec(encrypted, privateKey):
    return decrypt(privateKey, encrypted)


def generate_sasurl(url):
    # TODO get settings from config section
    bs = BlobService(account_name=settings.AZURE_ACCOUNT_NAME, account_key=settings.AZURE_ACCOUNT_KEY)
    today = datetime.datetime.utcnow()
    todayPlusMonth = today + datetime.timedelta(30)
    todayPlusMonthISO = todayPlusMonth.replace(microsecond=0).isoformat() + 'Z'
    sasToken = bs.generate_shared_access_signature(settings.AZURE_CONTAINER, None, SharedAccessPolicy(
        AccessPolicy(None, todayPlusMonthISO, "rw"), None))
    return url + "?" + sasToken
