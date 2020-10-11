from winreg import ConnectRegistry, EnumKey, OpenKeyEx, QueryValueEx, HKEY_CLASSES_ROOT

from ..util import RegKeyIter

import os
from xml.dom import minidom
from glob import glob

def getText(nodelist):
    res = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            res.append(node.data)
    return ''.join(res)


class WindowsStore:
    REPOSITORY_PATH = R"Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\Repository\Packages"
    LAUNCHER_ARGS = R"shell:appsFolder\{appid}_{publisher}!{exename}"

    __context = None
    __valid = False

    def __init__(self, context, settings):
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
        if item["item"]["logo_path"] is not None:
            # the logo_path is unfortunately not the actual file path, there may be different variants
            # for high-contrast and dpi scaled mods
            filepath, ext = os.path.splitext(item["item"]["logo_path"])
            relpath = os.path.dirname(filepath)
            basename = os.path.basename(filepath)

            # find all variations of the icon (contrast, scale)
            pattern = os.path.join(item["item"]["root_path"], relpath, "**", "{}*{}".format(basename, ext))
            # out of the icons we just use the one with the shortest name, should be the "basic"
            # one without further specifiers
            logos = list(sorted(glob(pattern, recursive=True), key = lambda x: len(x)))
            if len(logos) > 0:
                return logos[0]

        # if no other icon was found, try to get one from the exe
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

                logo_path = None
                try:
                    visuals = app.getElementsByTagName("uap:VisualElements")[0]
                    logo_path = visuals.getAttribute("Square150x150Logo")
                except Exception as e:
                    self.__context.warn("failed to get logo", exeid, e)

                id_parts = sub_key_name.split("_")
                games.append({
                    "appid": id_parts[0],
                    "publisher": id_parts[-1],
                    "name": name,
                    "exeid": exeid,
                    "root_path": root_path,
                    "exe_path": exe_path,
                    "logo_path": logo_path
                })
            except Exception as e:
                # This may be an error but most likely it's simply not a "proper" application we
                # could start. May be a service or something
                self.__context.dbg("manifest not parsed", e)

        return games
