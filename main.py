################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# main.py - application entrypoint

# imports
import os
from loguru import logger

import src.app as kiyo_app



# Start main loop.
if __name__ == '__main__':
    try:
        with kiyo_app.KiyokoApplication() as tmp_app:
            pass
    except Exception as tmp_e:
        logger.critical(tmp_e)

        os.abort()


