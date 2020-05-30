from winreg import ConnectRegistry, EnumKey, OpenKeyEx, QueryValueEx, HKEY_LOCAL_MACHINE

from ..util import RegKeyIter

import os
from urllib import parse

class UPlay:
    REG_INSTALL_PATH = R"SOFTWARE\WOW6432Node\Ubisoft\Launcher"
    REG_DETAILS_PATH = R"SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Uplay Install {appid}"
    LAUNCHER_CMD = "uplay://launch/${appId}/0"

    __context = None
    __valid = False
    def __init__(self, context):
        self.__context = context
        self.__valid = False

        self.__install_path = self.__get_install_path()

        self.__games = self.__read_manifest()

    def run(self, kpu, target, call_args):
        cmd = UPlay.LAUNCHER_CMD.format(appid=target)

        kpu.shell_execute(cmd)

    @property
    def items(self):
        return list(map(self.__to_catalog, self.__games))

    def fetch_icon(self, item, cache_path):
        return item["item"]["icon_path"]

    def __get_install_path(self):
        paths_key = OpenKeyEx(HKEY_LOCAL_MACHINE, UPlay.REG_INSTALL_PATH)
        return QueryValueEx(paths_key, "InstallDir")[0]

    def __to_catalog(self, item):
        return {
            "label": item["name"],
            "target": item["appid"],
            "item": item,
        }

    def __read_manifest(self):
        repository_key = OpenKeyEx(HKEY_LOCAL_MACHINE, UPlay.REG_INSTALL_PATH + R"\Installs")

        games = []

        for sub_key_name in iter(RegKeyIter(repository_key)):
            try:
                sub_key = OpenKeyEx(repository_key, sub_key_name)
                details_key = OpenKeyEx(HKEY_LOCAL_MACHINE, UPlay.REG_DETAILS_PATH.format(appid=sub_key_name))

                games.append({
                    "appid": sub_key_name,
                    "name": QueryValueEx(details_key, "DisplayName")[0],
                    "game_path": QueryValueEx(sub_key, "InstallDir")[0],
                    "icon_path": QueryValueEx(details_key, "DisplayIcon")[0],
                })
            except Exception as e:
                self.__context.err("Failed to read game", sub_key_name, e)

        return games
