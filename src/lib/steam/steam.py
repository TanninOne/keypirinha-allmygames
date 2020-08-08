import logging
import os
import subprocess
import time
from hashlib import sha1
from .vdf import load as vdfload, parse_appinfo
from ..util import CILookup
from functools import reduce
from winreg import ConnectRegistry, OpenKeyEx, QueryValueEx, HKEY_CURRENT_USER

def to_appinfo_dict(agg, input):
    agg[str(input["appid"])] = input
    return agg

def launcher_supported(game_path, launcher):
    # I don't actually know if the oslist is comma separated because I couldn't find
    # an example of a launcher that supported more than one os. how would it? why would it?
    supported_oses = launcher.get("config", {}).get(
        "oslist", "windows").split(",")
    if not "windows" in supported_oses:
        return False

    if "executable" in launcher and\
        not os.path.exists(os.path.join(game_path, launcher["executable"])):
        return False

    return True

def to_catalog(agg: list, game):
    if game["launchers"] is not None:
        is_supported = lambda idx: launcher_supported(game["path"], game["launchers"][idx])
        launchers = list(filter(is_supported, game["launchers"].keys()))
        for launcher_idx in launchers:
            launcher = game["launchers"][launcher_idx]
            label = game["name"]
            if len(launchers) > 1:
                label += " - " + launcher.get("description", "Default")

            entry = {
                "label": label,
                "target": launcher_idx + "|" + str(game["appid"]),
                "item": game,
            }
            if "executable" in launcher:
                entry["short_desc"] = launcher.get("executable", "") + " " + launcher.get("arguments", "")
            agg.append(entry)
    else:
        agg.append({
            "label": game["name"],
            "target": "|" + str(game["appid"]),
            "item": game,
        })
    return agg

def is_steam_running():
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    output, err = subprocess.Popen(["tasklist.exe",
                                    "/FI", "IMAGENAME eq steam.exe"],
                                    stdout=subprocess.PIPE).communicate()
    return str(output).find("steam.exe") != -1

class Steam:
    PATH = r"SOFTWARE\Valve\Steam"

    __context = None
    __valid = False
    __exe_path = None
    __install_path = None
    __appinfo = None

    def __init__(self, context):
        self.__context = context
        self.__valid = False
        self.__exe_path, self.__install_path = self.__get_install_path()
        context.info("install path", self.__install_path)
        self.__appinfo = self.__get_appinfo(self.__install_path)
        library_paths = self.__get_library_paths(self.__install_path)
        library_paths.insert(0, self.__install_path)
        context.info("libraries", library_paths)

        games = []
        for library in library_paths:
            games = games + self.__read_manifests(library)

        self.__games = games

    def run(self, kpu, target, call_args):
        launcher_id, appid = target.split("|", 1)
        if launcher_id != "":
            game = next(game for game in self.__games if game["appid"] == appid)
            launcher: dict = game["launchers"][launcher_id]
            if "executable" in launcher:
                self.__context.info("starting steam game with launcher", launcher)
                return self.run_directly(kpu, game, launcher, appid, call_args)

        return self.run_through_steam(kpu, appid, call_args)

    def run_directly(self, kpu, game: dict, launcher: dict, appid: str, call_args: str):
        args = None
        if "executable" in launcher:
            full_path = os.path.join(game["path"], launcher["executable"])
            os.environ["SteamAPPId"] = game["appid"]

            # since we're not running with steam -applaunch, steam will not be started
            # automatically but some games won't run correctly
            if not is_steam_running():
                self.__context.info("steam not running, starting it now")
                kpu.shell_execute(self.__exe_path)
                # arbitrary, is 5 seconds enough? I think as long as steam is starting up
                # the game will wait if necessary for it to complete initializing
                time.sleep(5)
            kpu.shell_execute(
                full_path,
                args=launcher.get("arguments", "") + " " + call_args,
                working_dir=launcher.get("workingdir", ""))

    def run_through_steam(self, kpu, appid: str, call_args: str):
        target = "-applaunch {} {}".format(appid, call_args)
        self.__context.info(
            "starting steam game through applaunch link", target)
        kpu.shell_execute(self.__exe_path, args=target)

    @property
    def items(self):
        return list(reduce(to_catalog, self.__games, []))

    def fetch_icon(self, item: object, cache_path):
        launcher_id, appid = item["target"].split("|", 1)

        # with steam we have multiple possible sources for the icon
        icon_path = None

        # if there is a launcher, this is the default case, we know where the executable is.
        # if it's actually an exe we use that because it usually provides the best quality icon.
        # Unfortunately we can't be sure if the exe does have an icon attached and it doesn't seem
        # like keypirinha has a way to let us check, so we may end up with entries with no icon at all
        if launcher_id != "":
            launcher = item["item"]["launchers"][launcher_id]
            if "executable" in launcher and os.path.splitext(launcher["executable"])[1] == ".exe":
                icon_path = "@{},0".format(os.path.join(item["item"]["path"], launcher["executable"]))

        if icon_path == None and item["item"]["icon_id"] != None:
            candidate = os.path.join(self.__install_path, "steam", "games", "{}.ico".format(item["item"]["icon_id"]))
            if os.path.exists(candidate):
                icon_path = candidate

        if icon_path == None:
            # _icon.jpg are only 32x32 so get very blurry and has no transparency
            candidate = os.path.join(self.__install_path, "appcache", "librarycache", "{}_icon.jpg".format(appid))
            if os.path.exists(candidate):
                icon_path = candidate

        if icon_path == None:
            # fallback to the steam icon
            icon_path = "@{},0".format(self.__exe_path)

        return icon_path

    def __get_install_path(self):
        try:
            root = ConnectRegistry(None, HKEY_CURRENT_USER)
            steam_key = OpenKeyEx(root, Steam.PATH)
            res_exe = QueryValueEx(steam_key, "SteamExe")
            res_path = QueryValueEx(steam_key, "SteamPath")
            self.__valid = True
            return res_exe[0], os.path.normpath(res_path[0])
        except Exception as e:
            self.__context.info("Failed to find path, maybe isn't installed", e)

    def __get_appinfo(self, install_path: str):
        with open(os.path.join(install_path, 'appcache', 'appinfo.vdf'), "rb") as fd:
            header, appinfo = parse_appinfo(fd)
            return reduce(to_appinfo_dict, appinfo, {})

    def __get_library_paths(self, install_path: str):
        with open(os.path.join(install_path, 'config', 'config.vdf')) as fd:
            # the vdf library is case sensitive but the format actually seems to
            # be case insensitive
            vdict = CILookup(vdfload(fd))
            base = vdict['InstallConfigStore']['Software']['Valve']['Steam']
            return list(map(
                lambda x: base[x],
                filter(lambda x: x.lower().startswith('baseinstallfolder_'),
                       base.keys())))

    def __read_manifests(self, library_path: str):
        is_manifest = lambda file_name: file_name.startswith('appmanifest_') and file_name.endswith('.acf')
        games = []

        apps_path = os.path.join(library_path, 'steamapps')
        for manifest_path in filter(is_manifest, os.listdir(apps_path)):
            try:
                with open(os.path.join(apps_path, manifest_path)) as fd:
                    manifest = vdfload(fd)
                    appid = manifest['AppState']['appid']
                    iconid = None
                    launchers = None
                    try:
                        appinfo = self.__appinfo[appid]["data"]["appinfo"]
                        iconid = appinfo["common"]["clienticon"]
                        launchers = appinfo["config"]["launch"]
                    except:
                        pass

                    games.append({
                        "appid": appid,
                        "name": manifest["AppState"]["name"],
                        "path": os.path.join(apps_path, "common", manifest["AppState"]["installdir"]),
                        "icon_id": iconid,
                        "launchers": launchers,
                    })
            except Exception as e:
                self.__context.warn("Failed to read manifest", manifest_path, e)
        return games
