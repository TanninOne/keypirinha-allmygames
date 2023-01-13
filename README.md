# Keypirinha Plugin: allmygames

This is allmygames, a plugin for the
[Keypirinha](http://keypirinha.com) launcher.

It adds all your games from various game stores to the catalog.
Currently supported stores:
- Steam
- Epic Games Store
- Windows Store
- GOG
- Origin
- UPlay

## Download

https://github.com/TanninOne/keypirinha-allmygames/releases


## Install

Once the `AllMyGames.keypirinha-package` file is downloaded,
move it to the `InstalledPackage` folder located at:

* `Keypirinha\portable\Profile\InstalledPackages` in **Portable mode**
* **Or** `%APPDATA%\Keypirinha\InstalledPackages` in **Installed mode** (the
  final path would look like
  `C:\Users\%USERNAME%\AppData\Roaming\Keypirinha\InstalledPackages`)

## Credits

* Uses vdf-parser by Rossen Georgiev: https://github.com/rossengeorgiev/vdf-parser

## Change Log

### v1.7
* support for new appinfo.vdf format (in beta as of this writing
* fixed: no steam games cataloged if steam config contains an invalid library folder

### v1.6
* made prefix for catalog items configurable

### v1.5
* fixed: steam game names not supporting utf8
* fixed: game not added to catalog if reading icon failed

### v1.4
* support for new steam config format

### v1.3
* code cleanup and log messages more standardized (thanks to ueffel)
* fixed: epic manifests read with wrong encoding (thanks to ueffel)
* added options to control which items steam adds

### v1.2
* allow disabling individual stores
* steam games are started via steam instead of running the exe
* fixed: uplay games not starting
* fixed: no steam entries if a defective manifest was encountered

### v1.1

* fixed: steam items in default library missing
* prefixing catalog items
* added icons for windows store items

### v1.0

* Initial release


## License

This package is distributed under the terms of the MIT license.

## Contribute
If you find any bugs or have suggestions for further features, please file an issue.

If you want to contribute directly to the code, just fork the repo, do your changes and create a pull request.

## Similar plugins

There are other plugins that add support for individual stores that you may want to look into.

There are often multiple ways to get at the information from those stores and these plugins may
have different approaches that may be more reliable than what allmygames does or less.

Steam (1): https://github.com/EhsanKia/keypirinha-plugins/tree/master/keypirinha-steam

Epic Games Store: https://github.com/samusaran/keypirinha-epiclauncher

GOG Galaxy: https://github.com/Torben2000/keypirinha-goggalaxy

Windows Apps: https://github.com/ueffel/Keypirinha-WindowsApps

(1) allmygames takes a different approach to starting steam games than keypirinha-steam. Allmygames will
offer the different start options that steam would offer for some games, whereas keypirinha-steam always starts
the default option (which is what most third party launchers do).
The approach in AMG has the drawback that you might find a lot of useless options in your catalog.

