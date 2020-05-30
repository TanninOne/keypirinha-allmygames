from winreg import ConnectRegistry, OpenKeyEx, QueryValueEx, HKEY_LOCAL_MACHINE

import json
import os

class EGS:
    LAUNCHER_PATH = R"SOFTWARE\WOW6432Node\Epic Games\EpicGamesLauncher"
    ICON_PATH = R"SOFTWARE\Classes\com.epicgames.launcher\DefaultIcon"
    LAUNCH_CMD = "com.epicgames.launcher://apps/{name}?action=launch&silent=true"

    __context = None
    __valid = False
    def __init__(self, context):
        self.__context = context
        self.__valid = False
        install_path = self.__find_store()
        context.info("install path", install_path)

        self.__exe_path = self.__get_exe_path()

        self.__games = self.__read_manifest(install_path)

    def run(self, kpu, appid, call_args):
        target = EGS.LAUNCH_CMD.format(name = appid)
        kpu.shell_execute(target)

    @property
    def items(self):
        return list(map(self.__to_catalog, self.__games))

    def fetch_icon(self, item, cache_path):
        return "@{},0".format(item["item"]["exe_path"])

    def __to_catalog(self, item):
        return {
            "label": item["name"],
            "target": str(item["appid"]),
            "item": item,
        }

    def __find_store(self):
        try:
            root = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
            base_key = OpenKeyEx(root, EGS.LAUNCHER_PATH)
            data_path = QueryValueEx(base_key, "AppDataPath")
            self.__valid = True
            return data_path[0]
        except Exception as e:
            self.__context.info("Failed to find path, maybe it isn't installed", e)

    def __get_exe_path(self):
        try:
            root = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
            base_key = OpenKeyEx(root, EGS.ICON_PATH)
            data_path = QueryValueEx(base_key, "")
            self.__context.info("data path", data_path)
            self.__valid = True
            return data_path[0].split(",")[0]
        except Exception as e:
            self.__context.info("Failed to find executable, maybe it isn't installed", e)

    def __read_manifest(self, install_path):
        manifest_path = os.path.join(install_path, "Manifests")

        is_manifest = lambda p: os.path.splitext(p)[1] == '.item'

        games = []

        for manifest_name in filter(is_manifest, os.listdir(manifest_path)):
            try:
                with open(os.path.join(manifest_path, manifest_name)) as fd:
                    manifest = json.load(fd)
                    if os.path.exists(manifest["InstallLocation"]):
                        games.append({
                            "appid": manifest['AppName'],
                            "name": manifest['DisplayName'],
                            "exe_path": os.path.join(manifest["InstallLocation"], manifest["LaunchExecutable"]),
                        })
            except Exception as e:
                self.__context.err("Failed to read manifest", manifest_name, e)

        return games
