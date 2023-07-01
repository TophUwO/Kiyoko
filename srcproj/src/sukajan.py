######################################################################
# Project:    Sukajan Bot v0.1                                       #
# File Name:  sukajan.py                                             #
# Author:     Sukajan One-Trick <tophuwo01@gmail.com>                #
# Description:                                                       #
#   a bot for the KirikoMains subreddit for advanced custom          #
#   features required by the moderation team                         #
#                                                                    #
# (C) 2023 Sukajan One-Trick. All rights reserved.                   #
######################################################################

# This file serves as the main entry point for the application.

# imports
import logging
import os

import client as sj_client


# Start main loop.
if __name__ == '__main__':
    try:
        with sj_client.SukajanClient() as tmp_client:
            pass
    except Exception as tmp_e:
        logging.critical(f'Fatal error: {tmp_e}')

        os.abort()


