from winreg import ConnectRegistry, OpenKeyEx, QueryValueEx, HKEY_LOCAL_MACHINE

import os
from urllib import parse

class Origin:
    PATH = r"SOFTWARE\WOW6432Node\Origin"
    LAUNCHER_CMD = "origin2://game/launch?offerIds={name}"

    __context = None
    __valid = False
    def __init__(self, context, settings):
        self.__context = context
        self.__valid = False
        self.__exe_path = self.__find_store()
        context.dbg("install path", os.path.dirname(self.__exe_path))

        self.__games = self.__read_manifest(self.__exe_path)

    def run(self, kpu, appid, call_args):
        target = Origin.LAUNCHER_CMD.format(name=appid)
        kpu.shell_execute(target)

    @property
    def items(self):
        return list(map(self.__to_catalog, self.__games))

    def fetch_icon(self, item, cache_path):
        # don't know how to find the exe or find an icon
        return "@{},0".format(self.__exe_path)

    def __to_catalog(self, item):
        return {
            "label": item["name"],
            "target": str(item["appid"]),
            "item": item,
        }

    def __find_store(self):
        try:
            root = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
            base_key = OpenKeyEx(root, Origin.PATH)
            data_path = QueryValueEx(base_key, "ClientPath")
            self.__valid = True
            return data_path[0]
        except Exception as e:
            self.__context.warn("Failed to find store path, maybe it isn't installed", e)

    def __read_manifest(self, install_path):
        manifests_path = os.path.join(os.environ["ProgramData"], "Origin", "LocalContent")

        is_manifest = lambda p: os.path.splitext(p)[1] == '.mfst'

        games = []

        for game_name in os.listdir(manifests_path):
            for manifest_name in filter(is_manifest, os.listdir(os.path.join(manifests_path, game_name))):
                try:
                    manifest_path = os.path.join(manifests_path, game_name, manifest_name)
                    with open(manifest_path) as fd:
                        manifest = fd.read()
                        # this is a pretty roundabout way to get rid of the leading ? but maybe a little bit more robust
                        # than simply taking a substring
                        par_raw = parse.urlparse("http://dummy/" + manifest).query.split('&')

                        parameters = dict(map(lambda i: parse.unquote(i).split("="), par_raw))
                        # there may be multiple manifests for dlcs and such, dipinstallpath is our marker for the "main"
                        # manifest. However, apparently it's only the path where the game was initially installed,
                        # if the game was moved this path wouldn't be valid any more
                        if "dipinstallpath" in parameters\
                            and (os.path.exists(parameters["dipinstallpath"]) or True):
                            self.__context
                            games.append({
                                "appid": parameters["id"],
                                "name": game_name,
                            })
                except Exception as e:
                    self.__context.err("Failed to read manifest", manifest_name, e)

        return games
