import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpnet

import os
import re
from glob import glob

from .lib.steam import Steam
from .lib.egs import EGS
from .lib.origin import Origin
from .lib.gog import GOG
from .lib.uplay import UPlay
from .lib.windowsstore import WindowsStore


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

class AllMyGames(kp.Plugin):

    CATEGORY = kp.ItemCategory.USER_BASE + 1

    """
    Add games from multiple game repositories to the catalog.

    ATM This adds all games we can find in Steam, Epic Games Store, GOG, Origin and
    the windows store to the catalog.
    """
    def __init__(self):
        super().__init__()

        self.__item_base = {
            "category": self.CATEGORY,
            "args_hint": kp.ItemArgsHint.ACCEPTED,
            "hit_hint": kp.ItemHitHint.KEEPALL,
        }
        self.__repos = {}
        self._debug = False

    def on_start(self):
        self.__settings = self.load_settings()

    def on_event(self, flags: int):
        if flags & kp.Events.PACKCONFIG:
            self.__settings = self.load_settings()

    def on_catalog(self):
        available_stores = [
            ("Steam", Steam),
            ("Epic Games Store", EGS),
            ("Windows Store", WindowsStore),
            ("GOG", GOG),
            ("Origin", Origin),
            ("UPlay", UPlay),
        ]
        # TODO: bethesda.net, rockstar launcher, battle.net

        stores = []
        for store in available_stores:
            if self.__settings.get_bool("enabled", store[0], True):
                stores.append(store)

        for candidate in stores:
            name, clazz = candidate
            try:
                self.__repos[name] = clazz(RepoContext(self, name))
            except Exception as e:
                # probably just not installed
                self.warn("failed to initialize repo", name, e)

        self.info("Games found", ["{}: {}".format(repo, len(self.__repos[repo].items)) for repo in self.__repos.keys()])

        catalog = []

        # update the repo-specific data with static and cached data
        for repo in self.__repos.keys():
            catalog.extend(self.make_item(repo, iter) for iter in self.__repos[repo].items)

        self.set_catalog(catalog)

    def on_execute(self, item, action):
        self.dbg("execute {}".format(item.data_bag()))
        repo, target = item.data_bag().split('|', 1)
        self.__repos[repo].run(kpu, target, item.raw_args())

    def make_item(self, repo: str, item: dict):
        icon_handle = self.get_icon(repo, item)
        valid_parameters = set(['category', 'label', 'target', 'short_desc', 'args_hint', 'hit_hint'])
        item = {k: v for k, v in item.items() if k in valid_parameters}
        item = {
            **self.__item_base,
            "short_desc": "Launch via {0}".format(repo),
            **item,
            "label": "AMG {}: {}".format(repo, item["label"]),
            "data_bag": repo + "|" + item["target"],
            "icon_handle": icon_handle,
        }
        return self.create_item(**item)

    def get_icon(self, repo: str, item: dict):
        cache_path = self.get_package_cache_path(create=True)
        target = re.sub(r"[<>:\"/\\|?*]", "_", item["target"])
        cache_icon_path: str = os.path.join(cache_path, "{repo}_{target}".format(repo=repo, target=target))

        cached = glob(cache_icon_path + ".*")
        if len(cached) > 0:
            cache_icon_path =  "cache://{}/{}".format(self.package_full_name(), os.path.basename(cached[0]))
        else:
            # if the icon has to be downloaded or is otherwise expensive to generate, the game script
            # can use the cache_icon_path parameter as the basis for the cache file
            # (appending the file extension)
            # either way they return a path is either
            # - a cache:// url if the script cached the icon itself
            # - a @<PE path> shell resource if it's an exe
            # - a regular file path
            # in the latter case we do the caching ourselves because load_icon doesn't support loading
            # files directly
            updated_path = self.__repos[repo].fetch_icon(item, cache_icon_path)

            if updated_path.startswith("cache://") or\
                updated_path.startswith("@"):
                cache_icon_path = updated_path
            else:
                ext = os.path.splitext(updated_path)[1]
                cache_icon_path += ext
                with open(updated_path, "rb") as file_in, \
                    open(cache_icon_path, "wb") as file_out:
                    file_out.write(file_in.read())
                cache_icon_path = "cache://{}/{}".format(
                    self.package_full_name(),
                    os.path.basename(cache_icon_path))

        self.dbg("icon cache path", cache_icon_path)
        return self.load_icon(cache_icon_path)

    def __make_context(self, id):
        return RepoContext(self, id)
