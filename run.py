import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

SERVER_FILES_PATH = Path('/home/artem/lugnica.pl/public/files')
FFMPEG_EXE_PATH = SERVER_FILES_PATH / 'ffmpeg.exe'
FFMPEG_ESSENTIALS_PATH = SERVER_FILES_PATH / Path('ffmpeg-release-essentials.exe')
FFMPEG_FULL_PATH = SERVER_FILES_PATH / ('ffmpeg-release-full.exe')

FFMPEG_ESSENTIALS_URL = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.7z'
FFMPEG_FULL_URL = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z'

VER_HOLDER = Path('./version')

logging.basicConfig(filename='runner.log', level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')


@dataclass
class FFmpegVariant:
    name: str
    download_url: str
    path: str
    server_version: Optional[str] = None


def should_update(variants: list[FFmpegVariant]) -> list[FFmpegVariant]:
    try:
        for variant in variants:
            variant.server_version = requests.get(variant.download_url, stream=True).url
    except:
        logging.error('Error contacting the gyan server.')
        sys.exit(1)

    if VER_HOLDER.exists():
        with open(VER_HOLDER, 'r+') as f:
            data = json.load(f)
            to_update = []
            
            for variant in variants:
                if data[variant.name] != variant.server_version:
                    to_update.append(variant)
                    data[variant.name] = variant.server_version
                
            if to_update:
                f.seek(0)
                f.write(json.dumps(data))
                f.truncate()
            return to_update
    else:
        with open(VER_HOLDER, 'w') as f:
            data = {}
            for variant in variants:
                data[variant.name] = variant.server_version
            f.write(json.dumps(data))
            logging.warning('New version file created, please restart the script.')
            sys.exit(1)


def extract_archive(archive_path: str) -> int:
    cmd = f'7z e "{archive_path}" -o"{SERVER_FILES_PATH}" "ffmpeg.exe" -r'
    p = subprocess.run(cmd, shell=True)
    return p.returncode


def update(to_update: list[FFmpegVariant]):
    for variant in to_update:
        name = variant.name
        url = variant.download_url
        path = variant.path

        r = requests.get(url)
        
        if not r.ok:
            logging.error(f'Request to {url} failed.')
            sys.exit(1)

        temp_archive = SERVER_FILES_PATH / f'temp-{int(time.time())}.7z'
        with open(temp_archive, 'wb') as f:
            f.write(r.content)

        extract_archive(temp_archive)
        FFMPEG_EXE_PATH.rename(path)
        
        temp_archive.unlink()
        logging.info(f'Successfully extracted {name} as {path}')


def main():
    ffmpeg_es = FFmpegVariant('ffmpeg-essentials', FFMPEG_ESSENTIALS_URL, FFMPEG_ESSENTIALS_PATH)
    ffmpeg_full = FFmpegVariant('ffmpeg-full', FFMPEG_FULL_URL, FFMPEG_FULL_PATH)
    variants = [ffmpeg_es, ffmpeg_full]

    logging.info('Checking for updates.')
    update_list = should_update(variants)
    if update_list:
        logging.info('New FFmpeg versions available, updating.')
        update(update_list)
    else:
        logging.info('Current FFmpeg variants are up to date, no action taken.')


if __name__ == '__main__':
    main()
