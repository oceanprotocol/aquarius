import logging
import os

logger = logging.getLogger(__name__)


def check_metadata_proofs(web3, metadata_proofs):
    try:
        allowed_validators = os.getenv("ALLOWED_VALIDATORS")

        if not allowed_validators:
            return True

        proof_addresses = [
            web3.toChecksumAddress(metadata_proofs.args.validator)
            for metadata_proof in metadata_proofs
        ]
        allowed_addresses = [
            web3.toChecksumAddress(address) for address in allowed_validators
        ]

        allowed_addresses = list(set(proof_addresses) & set(allowed_addresses))

        return bool(allowed_addresses)
    except Exception:
        logger.info("Exception retrieving proof addresses or validation proofs.")
        return False
