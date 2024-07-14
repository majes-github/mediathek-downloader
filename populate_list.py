#!/usr/bin/env python3
import argparse
import requests
import sys
from urllib import parse as urlparse

API = 'https://mediathekviewweb.de/api/query'
CHUNK_SIZE = 100


def parse_arguments():
    """Get commandline arguments."""
    parser = argparse.ArgumentParser('add downloads to mediathek-downloader')
    parser.add_argument('--directory', '-d', required=True,
                        help='where to store files')
    parser.add_argument('--search', '-s', required=True,
                        help='search pattern')
    parser.add_argument('--url', '-u', required=True,
                        help='URL of mediathek-downloader')
    parser.add_argument('--dry-run', action='store_true',
                        help='only show what is downloaded')
    parser.add_argument('--debug', action='store_true',
                        help='show debug messages')
    return parser.parse_args()


def get_episodes(pattern):
    query = {
        'queries': [
            {
                'fields': ['title', 'topic'],
                'query': pattern,
            },
        ],
        'sortBy': 'timestamp',
        'sortOrder': 'desc',
        'offset': 0,
        'size': CHUNK_SIZE,
    }
    episodes = []
    i = 0
    while i < 10:
        response = requests.post(API, json=query, headers={'Content-Type': 'text/plain'})
        episodes += response.json()['result']['results']
        info = response.json()['result']['queryInfo']
        result_count = info['resultCount']
        if not result_count:
            break
        query['offset'] += result_count
        i += 1
    return episodes


def add_task(mt_url, url, filename, directory, dry_run=False):
    params = locals()
    params.pop('mt_url')
    params.pop('dry_run')
    data = urlparse.urlencode(params, safe='')
    if dry_run:
        print(data)
    else:
        response = requests.post(mt_url, data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'})
        if response.status_code != 200:
            print('ERROR:', response.status_code, response.text)
            sys.exit(1)


def main():
    args = parse_arguments()
    for episode in get_episodes(args.search):
        title = episode['title']
        download_url = episode['url_video']
        url_video_hd = episode.get('url_video_hd')
        if url_video_hd:
            download_url = url_video_hd
        if not download_url.endswith('.mp4'):
            continue
        add_task(args.url, download_url, title, args.directory, args.dry_run)


if __name__ == '__main__':
    main()
