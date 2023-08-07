################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# res.py - resource manager for Kiyoko

# imports
import discord
import enum
import json
import easy_pil

from loguru      import logger
from dataclasses import dataclass



# resource types
class KiyokoResourceType(enum.Enum):
    LOCALIMG = 0 # image files saved on the local disk

# class holding a resource (url)
@dataclass
class KiyokoResource:
    id:    str                # id to use for referencing the resource
    type:  KiyokoResourceType # resource type
    url:   str                # resource URL



# class managing all resources used by Kiyoko
class KiyokoResourceManager(object):
    def __init__(self, app):
        self._app = app
        self._res: dict[str, KiyokoResource] = dict()


    # Reads the given .json file and loads all resources referenced
    # inside it.
    #
    # Returns nothing.
    def loadresources(self, fname: str) -> None:
        # Load JSON object, containing all resources to be loaded.
        try:
            logger.debug(f'Loading resource initialization file \'{fname}\'.')

            with open(fname, 'r') as tmp_fp:
                json_obj = json.load(tmp_fp)
        except Exception as tmp_e:
            logger.error(f'Could not read resource initialization file \'{fname}\'. Reason: {tmp_e}')

            return

        # Check if all required resources are present.
        reqkeys  = json_obj.get('required', None)
        res2load = json_obj.get('resources', None)
        for key in reqkeys:
            # Check if key exists.
            if not any(obj['id'] == key for obj in res2load):
                logger.warning(f'Could not find required resource in list: \'{key}\'.')
            
        
        # Load all resources in the list.
        n = 0
        for res in res2load:
            # Inpack dict.
            (rid, url) = res.values()

            # Check if URL is valid.
            try:
                tmp_edit = easy_pil.Editor(url)
            except Exception as tmp_e:
                logger.warning(f'URL for resource \'{rid}\' is invalid. Reason: {tmp_e}')

                continue

            # Register the resource.
            self.regresource(rid, url)
            n += 1

        # Send info message.
        logger.debug(f'Loaded {n} of {len(res2load)} resources from \'{fname}\'.')


    # Creates a new resource object and stores it inside
    # the resource manager dictionary.
    #
    # Returns nothing.
    def regresource(self, rid: str, url: str) -> None:
        # Construct resource object and insert it into the dictionary.
        self._res[rid] = KiyokoResource(rid, KiyokoResourceType.LOCALIMG, url)

        # Everything went well.
        logger.debug(f'Registered resource \'{rid}\' (url: {url}).')


