from discord.ext.commands import CommandError


class AdventureBase(CommandError):
    """ Base exception for my special errors. """
    pass


class AlreadyTravelling(AdventureBase):
    def __init__(self, *stuff):
        super().__init__("%s is already travelling! He will return in %s." % stuff)


class PlayerExists(AdventureBase):
    def __init__(self, player):
        super().__init__("You already own someone named \"%s\"!" % player)


class NotNearby(AdventureBase):
    def __init__(self, map1, map2):
        super().__init__("%s isn't nearby %s. This is a limitation, I haven't created this much." % (map1, map2))
