import keypirinha as kp

class RepoContext:
    def __init__(self, plugin: kp.Plugin, id: str):
        """ Proxy for the kp.Plugin object passed to the individal repository implementations

        Arguments:
            plugin {[kp.Plugin]} -- The plugin to wrap
            id {[string]} -- ID of the repository this is used with. Will be prepended to all log messages
        """
        self.__plugin = plugin
        self.__id = id

    def dbg(self, msg: str, *args):
        return self.__plugin.dbg("[{id}] {msg}".format(id=self.__id, msg=msg), *args)

    def info(self, msg: str, *args):
        return self.__plugin.info("[{id}] {msg}".format(id=self.__id, msg=msg), *args)

    def warn(self, msg: str, *args):
        return self.__plugin.warn("[{id}] {msg}".format(id=self.__id, msg=msg), *args)

    def err(self, msg: str, *args):
        return self.__plugin.err("[{id}] {msg}".format(id=self.__id, msg=msg), *args)

    @property
    def plugin(self):
        return self.__plugin

