from winreg import ConnectRegistry, EnumKey, OpenKeyEx, QueryValueEx, HKEY_LOCAL_MACHINE

from ..util import RegKeyIter

import os
from urllib import parse

class GOG:
    CLIENT_PATH = R"SOFTWARE\WOW6432Node\GOG.com\GalaxyClient\paths"
    CLIENT_EXE = "GalaxyClient.exe"
    GAMES_PATH = R"SOFTWARE\WOW6432Node\GOG.com\Games"
    LAUNCHER_ARGS = "/command=runGame /gameId={appid} path={game_path}"

    __context = None
    __valid = False
    def __init__(self, context, settings):
        self.__context = context
        self.__valid = False
        self.__exe_path = self.__get_exe_path()
        self.__games = self.__read_manifest()

    def run(self, kpu, target, call_args):
        appid, game_path = target.split('|', 1)
        args = GOG.LAUNCHER_ARGS.format(appid=appid, game_path=game_path)

        kpu.shell_execute(self.__exe_path, args=args)

    @property
    def items(self):
        return list(map(self.__to_catalog, self.__games))

    def fetch_icon(self, item, cache_path):
        return "@{},0".format(item["item"]["exe_path"])

    def __get_exe_path(self):
        paths_key = OpenKeyEx(HKEY_LOCAL_MACHINE, GOG.CLIENT_PATH)
        client_path = QueryValueEx(paths_key, "client")[0]
        return os.path.join(client_path, GOG.CLIENT_EXE)

    def __to_catalog(self, item):
        return {
            "label": item["name"],
            "target": item["appid"] + "|" + item["game_path"],
            "item": item,
        }

    def __read_manifest(self):
        repository_key = OpenKeyEx(HKEY_LOCAL_MACHINE, GOG.GAMES_PATH)

        games = []

        for sub_key_name in iter(RegKeyIter(repository_key)):
            try:
                sub_key = OpenKeyEx(repository_key, sub_key_name)

                exe = QueryValueEx(sub_key, "EXE")[0]
                if os.path.exists(exe):
                    games.append({
                        "appid": QueryValueEx(sub_key, "gameID")[0],
                        "name": QueryValueEx(sub_key, "startMenu")[0],
                        "game_path": QueryValueEx(sub_key, "path")[0],
                        "exe_path": exe,
                    })
                else:
                    self.__context.warn("not found", exe)
            except Exception as e:
                self.__context.warn("Failed to read game info", sub_key_name, e)

        return games
