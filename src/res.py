################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# res.py - resource manager for Kiyoko

# imports
import enum, json, easy_pil

from typing      import Optional, Self
from loguru      import logger
from dataclasses import *



# resource types
class KiyokoResourceType(enum.Enum):
    INVALID  = -1 # invalid type, denotes error
    LOCALIMG = 0  # image files saved on the local disk


# class holding a resource (url)
@dataclass
class KiyokoResource:
    id:    str                # id to use for referencing the resource
    type:  KiyokoResourceType # resource type
    url:   Optional[str] = '' # resource URL

    # Updates a resource. Only updates the fields that are given.
    #
    # Returns nothing.
    def update(self, **kwargs) -> Self:
        # Save current state.
        old = replace(self)

        # Update given fields.
        self.url = kwargs.get('url', self.url)

        # Return old state.
        return old



# class managing all resources used by Kiyoko
class KiyokoResourceManager(object):
    def __init__(self, app):
        self._app = app
        self._res: dict[str, KiyokoResource] = dict()

        # Get root of resource directory.
        rpath = self._app.cfg.getvalue('global', 'resinitpath')
        if rpath is not None:
            # Load all resources.
            self.loadresources(rpath)


    # Reads the given .json file and loads all resources referenced
    # inside it.
    #
    # Returns nothing.
    def loadresources(self, fname: str) -> None:
        # Load JSON object, containing all resources to be loaded.
        try:
            logger.debug(f'Reading resource initialization file \'{fname}\'.')

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
            (rid, url) = res.values()

            # Check if URL is valid. Also try to open the image. This way,
            # we can also catch if the file pointed to is not an image or
            # whether the image file is corrupted.
            try:
                tmp_edit = easy_pil.Editor(url)
            except Exception as tmp_e:
                logger.warning(f'URL for resource \'{rid}\' is invalid. Reason: {tmp_e}')

                continue

            # Register the resource.
            self.regresource(rid, KiyokoResourceType.LOCALIMG, url = url)
            n += 1

        # Send info message.
        logger.debug(f'Loaded {n} of {len(res2load)} resources from \'{fname}\'.')


    # Creates a new resource object and stores it inside the resource
    # manager dictionary.
    #
    # Returns nothing.
    def regresource(self, rid: str, ty: KiyokoResourceType, **kwargs) -> None:
        # Construct resource object and insert it into the dictionary.
        self._res[rid] = KiyokoResource(
            rid,
            ty,
            **kwargs
        )

        # Everything went well.
        logger.debug(f'Registered resource \'{rid}\' (type: {ty.name}).')


    # Removes a resource object from the internal storage. After this call,
    # it cannot be retrieved any longer.
    # If the resource ID is not registered, this function does nothing.
    #
    # Returns old resource object. If the resource ID is not registered,
    # the function returns None.
    def unregresource(self, rid: str) -> KiyokoResource:
        found = None
        
        try:
            found = self._res.pop(rid)
        except KeyError:
            pass

        return found


    # Updates an already registered resource. Note that the ID and the resource type
    # cannot be changed retroactively.
    #
    # Returns old resource info. If the resource with the given ID is not registered,
    # the function returns None. The resource storage is not touched.
    def updresource(self, rid: str, **kwargs) -> KiyokoResource:
        # Update resource and return previous one.
        return self._res[rid].update(**kwargs) if self.getresource(rid) is not None else None


    # Retrieves a resource with a given identifier.
    #
    # Returns resource object, or None if the resource could not be found.
    def getresource(self, rid: str) -> KiyokoResource:
        return self._res.get(rid, None)


