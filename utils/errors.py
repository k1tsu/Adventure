from discord.ext.commands import CommandError
import blobs


class AdventureBase(CommandError):
    """ Base exception for my special errors. """
    pass


class AlreadyTravelling(AdventureBase):
    def __init__(self, *stuff):
        super().__init__("{0} {1} is busy and will finish in {2}".format(blobs.BLOB_ARMSCROSSED, *stuff))


class AlreadyExplored(AdventureBase):
    def __init__(self, _map):
        super().__init__("%s %s is already explored!" % (blobs.BLOB_ARMSCROSSED, _map))


class PlayerExists(AdventureBase):
    def __init__(self, player):
        super().__init__("%s You already own someone named \"%s\"!" % (player, blobs.BLOB_ARMSCROSSED))


class NotNearby(AdventureBase):
    def __init__(self, map1, map2):
        super().__init__("%s isn't nearby %s. This is a limitation, I haven't created this much." % (map1, map2))


class Blacklisted(AdventureBase):
    def __init__(self, reason):
        super().__init__("You have been blacklisted for: %s" % reason)
