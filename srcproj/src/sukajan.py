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
    print(
        '''######################################################################\n'''
        '''# Project:    Sukajan Bot v0.1                                       #\n'''
        '''# Author:     Sukajan One-Trick <tophuwo01@gmail.com>                #\n'''
        '''# Description:                                                       #\n'''
        '''#   a bot for the KirikoMains subreddit for advanced custom          #\n'''
        '''#   features required by the moderation team                         #\n'''
        '''#                                                                    #\n'''
        '''# (C) 2023 Sukajan One-Trick. All rights reserved.                   #\n'''
        '''######################################################################\n'''
        '''\n\n'''
    )

    try:
        with sj_client.SukajanClient() as tmp_client:
            pass
    except Exception as tmp_e:
        logging.critical(f'Fatal error: {tmp_e}')

        os.abort()

    print('Shutdown ...\n')


