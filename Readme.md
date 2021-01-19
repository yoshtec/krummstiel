# Krummstiel

Krummstiel is a small Python script automating regular backup apple ios device. The idea is to incrementally save 
pictures to your server/desktop. It is in use on Linux, but could be run on macOS as well with the proper tools 
installed. 

## Features

Implemented: 

* Automatically mount and copy Files to Backup path via rsync for configured and connected devices.
* Configuration of backup path
* Configure excluded paths globally or per Device
* Help in connecting new devices 
* Silently ignore disconnected devices

Planned Features:
* Notify user of the backup start and finished on the device
* Delete old photos and videos from the device after backup. Should understand not to delete Favourites or specified 
  albums. For that the `Photos.sqlite` database has to be read and understood. My efforts to understand the database 
  are found in [photossqlite.md](photossqlite.md) File.
* Backup application data

## Get Started

1. Install required tools and libraries:  
   Linux (Ubuntu 20.4):
   ```shell
   apt install libimobiledevice6 libimobiledevice-utils ifuse rsync 
   ```
   macOS:
   ```shell
   brew install --cask osxfuse
   brew install libimobiledevice ifuse 
   ```
1. Install krummstiel via
    ```shell
    pip install krummstiel
    ```
1. Create a target directory that will contain the backups e.g. via `mkdir /mnt/data/iphone_backups`
1. Create your config file from [example.ini](example.ini)
1. Discover connected devices via
    ```shell
    krummstiel --discover --config "/path/to/myconfig.ini"
    ```
1. run the script via:
    ```shell
    krummstiel --config "/path/to/myconfig.ini" --verbose
    ```


## Config

Configuration is done via .ini File and is passed via `--config` or `-c` parameter.
 ```ini
 
[DEFAULT]

# path fo the backup, the name of the device will always be appended
backup_path = /mnt/data/iphone_backups

# excludes can be an json array or a single value see example of iphone1
# format is for rsync --exclude syntax
exclude = Podcasts

# Section naming will be used for identifying the ios device
# Section is the uid of the ios device
[1234567890abcdef1234567890abcdef12345678]
# name is used to create the folder and copy files
name = my_iphone
# exclude can be repeated and is overriding exclude of the DEFAULT section
# json array
exclude = ["Podcasts", "Books"]
```

## Automating with UDEV (Linux only)
[Udev](https://linux.die.net/man/8/udev) allows you to run scripts when devices are plugged in.

Examples: 
* <https://unix.stackexchange.com/questions/28548/how-to-run-custom-scripts-upon-usb-device-plug-in>
* <https://github.com/justinpearson/Raspberry-Pi-for-iPhone-Backup#4a-udev-example>

## Automating with cron
Krummstiel can just run regularly with as a cronjob. Running it with your user ensures that you have access to the files backed up.
```shell
*/5 *    * * *   your_user_id    path/to/krummstiel --config "path/to/config.ini" >> /path/to/backup.log
```

# Name 
The name of the program was chosen to be an Apple that is under threat. One would assume that apples are ubiquitous 
and are in status "least concern", while this is true for many apples (especially for commercially used and still 
distributed apples) there are many apple types that are endangered. 

The [Rheinischer Krummstiel](https://de.wikipedia.org/wiki/Rheinischer_Krummstiel) is an old 
apple variant which is on the "[Red list of endagered domestic plants](https://pgrdeu.genres.de/rlist)" of the German 
"[Federal Office for Agriculture and Food](https://www.ble.de/EN/Home/home_node.html)". It can roughly be translated 
to "crooked stalk", which I found a good analogy for attaching the Apple device to an usb cable.   

There are more apples, that are under threat visit the [IUCN Threatened Species list](https://www.iucnredlist.org) for 
a full list of all species.

# License

Krummstiel uses the MIT License.