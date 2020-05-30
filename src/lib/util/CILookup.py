class CILookup:
    """
    Wrapper around a dictionary that allows case-insensitve lookups
    """
    def __init__(self, wrapped):
        self.__wrapped = wrapped
        self.__keymap = {}
        for key in wrapped.keys():
            self.__keymap[key.casefold()] = key

    def __getitem__(self, key):
        realkey = self.__keymap[key.casefold()]
        res = self.__wrapped[realkey]
        if isinstance(res, dict):
            res = CILookup(res)
        return res

    def keys(self):
        return self.__wrapped.keys()

    def __repr__(self):
        return self.__wrapped.__repr__()

    def __str__(self):
        return self.__wrapped.__str__()
