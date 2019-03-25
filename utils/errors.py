# -> Pip packages
from discord.ext.commands import CommandError

# -> Local files
import blobs


class AdventureBase(CommandError):
    """ Base exception for my special errors. """
    pass


class AlreadyTravelling(AdventureBase):
    def __init__(self, *stuff):
        super().__init__("{} {} is busy and will finish in {}".format(blobs.BLOB_ARMSCROSSED, *stuff))


class AlreadyExplored(AdventureBase):
    def __init__(self, _map):
        super().__init__("{} {} is already explored!".format(blobs.BLOB_ARMSCROSSED, _map))


class PlayerExists(AdventureBase):
    def __init__(self, player):
        super().__init__("{} You already own someone named \"{}\"!".format(player, blobs.BLOB_ARMSCROSSED))


class NotNearby(AdventureBase):
    def __init__(self, map1, map2):
        super().__init__("{} isn't nearby {}. This is a limitation, I haven't created this much.".format(map1, map2))


class Blacklisted(AdventureBase):
    def __init__(self, reason):
        super().__init__("You have been blacklisted for: {}".format(reason))


class IgnoreThis(AdventureBase):
    def __init__(self):
        pass
