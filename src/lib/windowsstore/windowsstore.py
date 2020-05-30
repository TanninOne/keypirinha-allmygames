from winreg import ConnectRegistry, EnumKey, OpenKeyEx, QueryValueEx, HKEY_CLASSES_ROOT

from ..util import RegKeyIter

import os
from xml.dom import minidom

class WindowsStore:
    REPOSITORY_PATH = R"Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\Repository\Packages"
    LAUNCHER_ARGS = R"shell:appsFolder\{appid}_{publisher}!{exename}"

    __context = None
    __valid = False
    def __init__(self, context):
        self.__context = context
        self.__valid = False
        self.__games = self.__read_repository()

    def run(self, kpu, target, call_args):
        appid, publisher, exeid = target.split('|')
        args = WindowsStore.LAUNCHER_ARGS.format(
            appid=appid,
            publisher=publisher,
            exename=exeid
        )

        kpu.shell_execute("explorer.exe", args=args)

    @property
    def items(self):
        return list(map(self.__to_catalog, self.__games))

    def fetch_icon(self, item, cache_path):
        exe_path = os.path.join(item["item"]["root_path"], item["item"]["exe_path"])
        return "@{},0".format(exe_path)

    def __to_catalog(self, item):
        return {
            "label": item["name"],
            "target": "{appid}|{publisher}|{exeid}".format(appid=item["appid"], publisher=item["publisher"], exeid=item["exeid"]),
            "item": item,
        }

    def __read_repository(self):
        root = ConnectRegistry(None, HKEY_CLASSES_ROOT)
        base_key = OpenKeyEx(root, WindowsStore.REPOSITORY_PATH)
        idx = 0
        games = []

        for sub_key_name in iter(RegKeyIter(base_key)):
            try:
                sub_key = OpenKeyEx(base_key, sub_key_name)
                idx += 1
                name = QueryValueEx(sub_key, "DisplayName")[0]
                if name.startswith("@{"):
                    # if it doesn't have a name we don't care for it
                    continue
                root_path = QueryValueEx(sub_key, "PackageRootFolder")[0]

                doc = minidom.parse(os.path.join(root_path, "appxmanifest.xml"))

                apps = doc.getElementsByTagName("Application")
                if apps.length == 0:
                    continue
                app = apps[0]

                exeid = app.getAttribute("Id")
                exe_path = app.getAttribute("Executable")

                id_parts = sub_key_name.split("_")
                games.append({
                    "appid": id_parts[0],
                    "publisher": id_parts[-1],
                    "name": name,
                    "exeid": exeid,
                    "root_path": root_path,
                    "exe_path": exe_path,
                })
            except Exception as e:
                # This may be an error but most likely it's simply not a "proper" application we
                # could start. May be a service or something
                self.__context.dbg("manifest not parsed", e)

        return games
