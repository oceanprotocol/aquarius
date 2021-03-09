import os
from abc import ABC

from aquarius.app.util import get_bool_env_value


class BlockProcessingClass(ABC):
    @property
    def block_envvar(self):
        return ""

    def get_or_set_last_block(self):
        ignore_last_block = get_bool_env_value("IGNORE_LAST_BLOCK", 0)
        _block = int(os.getenv(self.block_envvar, 0))
        try:
            if ignore_last_block:
                self.store_last_processed_block(_block)

                return _block

            return self.get_last_processed_block()
        except Exception:
            self.store_last_processed_block(_block)

            return _block
