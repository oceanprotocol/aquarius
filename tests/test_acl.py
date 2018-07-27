from provider_backend.acl.acl import encode, decode, enc, dec, generate_encription_keys, generate_encoding_pair


def test_encode_decode():
    pubprivkey = generate_encoding_pair()
    encod = encode({"metadata": "example"}, pubprivkey.private_key)
    assert {"metadata": "example"} == decode(encod, pubprivkey.public_key)


def test_encrypt_decrypt():
    provider_keypair = generate_encoding_pair()
    consumer_keypair = generate_encription_keys()
    encod = encode({"metadata": "example"}, provider_keypair.private_key)
    encrypt = enc(encod, consumer_keypair.public_key)
    decrypt = dec(encrypt, consumer_keypair.private_key)
    assert {"metadata": "example"} == decode(decrypt, provider_keypair.public_key)
