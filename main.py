import qbittorrentapi
from os import environ
from dotenv import load_dotenv
import re
from loguru import logger

import os
import sys
from glob import glob



load_dotenv()

qbt_login = environ.get("QBITTORRENT_LOGIN")
qbt_password = environ.get("QBITTORRENT_PASSWORD")
qbt_host = environ.get("QBITTORRENT_HOST")

qbt_client = qbittorrentapi.Client(host=qbt_host, username=qbt_login, password=qbt_password)
qbt_client.auth_log_in()

torrents = qbt_client.torrents_info()

def find_torrent(path):
    # Replace /srv/torrents by nothing (to match the qbittorrent container file system)
    path = re.sub(r'^/srv/torrents', '', path)

    for torrent in torrents:
        if torrent.content_path == path:
            return torrent

def delete_torrent(torrent):
    logger.warning(f'Delete torrent {torrent.name}')
    qbt_client.torrents_delete(delete_files=True, torrent_hashes=torrent.hash)


def recurse_list(path):
    for root, directory, files in os.walk(path):
        for file in files:
            yield os.path.join(root, file)


for service in ('sonarr', 'radarr'):
    for file_path in glob(f'/srv/torrents/data/downloads/{service}/*'):
        # If the file is a file, check if it has one link
        if os.path.isfile(file_path):
            stat = os.stat(file_path)

            if stat.st_nlink == 1:
                torrent = find_torrent(file_path)
                delete_torrent(torrent)
                print(f"Deleted {file_path}")

        # If the file is a dir, check if one file has 2 symlinks => all files have one link
        if os.path.isdir(file_path):
            a = list(recurse_list(file_path))

            is_useless = True

            for subfile_path in a:

                stat = os.stat(subfile_path)

                if stat.st_nlink > 1:
                    is_useless = False
                    break

            # If useless, delete the file
            if is_useless:
                torrent = find_torrent(file_path)
                delete_torrent(torrent)
                print(f"Deleted {file_path}")

qbt_client.auth_log_out()
