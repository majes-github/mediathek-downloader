#!/usr/bin/env python3

import argparse
import json
import os
import random
import requests
from threading import Lock, Thread
import time

import flask
from flask import flash, redirect, render_template, request, Response

from config import Config


app = flask.Flask(__name__)
app.config.from_object(Config)

FILENAME = 'schedule.json'
exit_download_loop = False
base_dir = None


class Element(object):
    lock = Lock()
    origin_accepts_range_header = False
    size = 0
    bytes_read = 0
    receive_rate = 0   # bytes per second
    ref_ts = 0
    ref_bytes = 0

    def __init__(self, url, name, dir=None):
        self.url = url
        self.name = name
        self.dir = dir
        self.size, self.origin_accepts_range_header = self.accepts_range_header()
        # TODO: assign uuid to element (for removal)

    def __repr__(self):
        return self.url

    def to_dict(self):
        keys = ('url', 'name', 'dir')
        return {k: v for k, v in self.__dict__.items() if k in keys and v}

    def accepts_range_header(self):
        r = requests.head(self.url)
        size = int(r.headers.get('Content-Length', 0))
        accept_ranges = r.headers.get('Accept-Ranges', None) == 'bytes'
        return size, accept_ranges

    # def get_bytes_read(self):
    #     with self.lock:
    #         return self.bytes_read
    #
    def add_bytes_read(self, bytes):
        with self.lock:
            self.bytes_read += bytes

    # def get_receive_rate(self):
    #     with self.lock:
    #         return self.receive_rate
    #
    def set_receive_rate(self, rate):
        with self.lock:
            self.receive_rate = rate

    def set_ref_ts(self, ts):
        with self.lock:
            self.ref_ts = ts

    def set_ref_bytes(self):
        with self.lock:
            self.ref_bytes = self.bytes_read

    def get_percent(self):
        return int(self.bytes_read / self.size * 100)


class Schedule(object):
    lock = Lock()
    elements = []
    #current_element = None
    limit_rate = 100000
    frequency = 100  #  do not iterate over chunks more than frequency (in order to reduce cpu load)
    slot_time = 1 / frequency
    chunk_size = 2**20   # 1 Mbyte
    pause = False

    def __init__(self):
        with self.lock:
            self.read_file()
        self.set_limit_rate(self.limit_rate)

    def read_file(self):
        try:
            with open(FILENAME) as fd:
                content = json.load(fd)
                self.elements = [Element(**e) for e in content['elements']]
                self.limit_rate = content.get('limit_rate', 0)
                self.pause = content.get('pause', False)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            pass

    def write_file(self):
        # Remove duplicates
        urls = []
        for element in self.elements.copy():
            url = element.url
            if url not in urls:
                urls.append(url)
            else:
                self.elements.remove(element)

        with open(FILENAME, 'w') as fd:
            json.dump({
                'elements': [e.to_dict() for e in self.elements],
                'limit_rate': self.limit_rate,
                'pause': self.pause,
            }, fd)

    def add_element(self, element):
        with self.lock:
            self.elements.append(element)
            self.write_file()

    def remove_element(self, element):
        with self.lock:
            self.elements.remove(element)
            self.write_file()

    def remove_head(self):
        with self.lock:
            head = self.current_element
            self.current_element = None
        self.remove_element(head)

    def get_elements(self):
        with self.lock:
            return self.elements.copy()

    def get_head(self):
        with self.lock:
            try:
                self.current_element = self.elements[0]
                return self.current_element
            except IndexError:
                return None

    def get_next(self):
        with self.lock:
            try:
                return self.elements[1]
            except IndexError:
                return None

    def get_current_element(self):
        with self.lock:
            return self.elements[0] if self.elements else None

    def set_limit_rate(self, rate):
        with self.lock:
            self.limit_rate = rate
            self.chunk_size = int(rate / self.frequency)

    # def get_pause(self):
    #     with self.lock:
    #         return self.pause

    def set_pause(self):
        with self.lock:
            self.pause = True

    def set_resume(self):
        with self.lock:
            self.pause = False


def bytes_to_human(bytes, html=False):
    """Returns a human readable string reprentation of bytes."""
    units = ['Bytes', 'kB', 'MB', 'GB', 'TB', 'PB', 'EB']
    spacer = '&nbsp;' if html else ' '
    for unit in units:
        if bytes < 1024:
            break
        bytes /= 1024.0
    if bytes >= 100:
        bytes_str = int(bytes)
    else:
        bytes_str = '{:{prec}}'.format(
            float(bytes), prec='.3').replace('.', ',')
        if bytes_str.endswith(',0'):
            bytes_str = bytes_str.split(',')[0]
    human = '{}{}{}'.format(bytes_str, spacer, unit)
    return human


@app.route('/', methods=['GET', 'POST'])
def home():
    message = None
    if request.form:
        url = request.form.get('url')
        filename = request.form.get('filename')
        directory = request.form.get('directory')
        print('Add download:', url, filename, directory)
        schedule.add_element(Element(url, filename, directory))
        flash('Download hinzugefügt: {}'.format(filename))
        return redirect('/')

    parameters = {
        'directories': [d for d in os.listdir(base_dir)
                        if os.path.isdir(os.path.join(base_dir, d))],
    }
    return render_template('index.html', **parameters)


@app.route('/pause')
def pause_download():
    schedule.set_pause()
    if True:
        # TODO: check if download could be paused
        return ''
    else:
        return Response('Could not pause download.\n', status=400)


@app.route('/resume')
def resume_download():
    schedule.set_resume()
    if True:
        # TODO: check if download could be resumed
        return ''
    else:
        return Response('Could not resume download.\n', status=400)


@app.route('/add', methods=['POST'])
def add():
    parameters = request.json
    url = parameters.get('url')
    name = parameters.get('name')
    dir = parameters.get('dir')
    if url and name:
        schedule.add_element(Element(url, name, dir))
        return redirect('/')
    else:
        return Response('Parameters url and name are mandatory.\n', status=400)


@app.route('/status')
def status():
    current = schedule.get_current_element()
    data = {
        'elements': [
            {'name':  element.name, 'size': bytes_to_human(element.size)}
            for element in schedule.elements],
        'pause': schedule.pause,
        'limit_rate': schedule.limit_rate,
    }
    if current:
        data['download_rate'] = '{} kB/s'.format(
            int(current.receive_rate / 1000))
        data['current_percent'] = current.get_percent()
    return data


@app.route('/limit_rate/<int:rate>')
def limit_rate(rate):
    schedule.set_limit_rate(rate)
    return redirect('/')


@app.route('/delete/<id>')
def delete(rate):
    #schedule.set_limit_rate(rate)
    return redirect('/')


def download_loop():
    current = None
    previous_paused = None
    # while not exit_download_loop:
    while True:
        if previous_paused is None:
            previous_paused = schedule.pause
        if previous_paused != schedule.pause:
            print('Schedule', 'paused' if schedule.pause else 'resumed')
            previous_paused = schedule.pause
        if schedule.pause:
            time.sleep(1)
            continue

        if current:
            if not r.raw.closed:
                # calculate amount of bytes to read
                # (based on frequency and limit_rate)
                before_ts = time.time()
                # download chunk
                chunk = r.raw.read(schedule.chunk_size)
                fd.write(chunk)
                after_ts = time.time()
                chunk_time = after_ts - before_ts
                current.add_bytes_read(len(chunk))

                # update receive rate about every second
                delta_ts = after_ts - current.ref_ts
                if delta_ts > 1:
                    rate = int((
                        current.bytes_read - current.ref_bytes) / delta_ts)
                    #print('current download rate is {} bytes per second'.format(rate))
                    current.set_receive_rate(rate)
                    current.set_ref_ts(after_ts)
                    current.set_ref_bytes()
                    fd.flush()

                # rate limiting
                if chunk_time < schedule.slot_time:
                    time.sleep(schedule.slot_time - chunk_time)
                continue
            else:
                fd.close()

        current = schedule.get_head()
        if not current:
            print('No download available. Waiting for new downloads...')
            time.sleep(1)
            continue
        #print('Next element:', current.name)

        # define file extension if there is no extension in element name
        if '.' in current.name:
            file_name = current.name
        else:
            location = current.url.split('/')[-1]
            extension = 'mp4'  # default
            if '.' in location:
                extension = location.split('.')[-1]
            file_name = '{}.{}'.format(current.name, extension)
        file_name = file_name.replace('/', '_')
        if current.dir:
            file_name = os.path.join(current.dir.strip('/'), file_name)

        # prefix file_name by base_dir commandline argument
        file_name = os.path.join(base_dir, file_name)

        # do not transport gzip'ed data (makes no sense for videos anyways)
        headers = {'Accept-Encoding': ''}

        # if file exists - try to continue
        if os.path.exists(file_name) and current.origin_accepts_range_header:
            file_size = os.path.getsize(file_name)
            if file_size == current.size:
                print('File has been already downloaded:', file_name)
                schedule.remove_head()
                current = None
                time.sleep(1)
                continue
            fd = open(file_name, 'ab')
            headers['Range'] = 'bytes={}-'.format(file_size)
            current.add_bytes_read(file_size)
        else:
            fd = open(file_name, 'wb')
        r = requests.get(current.url, headers=headers, stream=True)
    print('Stopping download loop')


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Mediathek download utility.')
    parser.add_argument('--base-dir', default='/tmp/video',
                        help='root directory for downloads')
    return parser.parse_args()


def main():
    global schedule
    global exit_download_loop
    global base_dir
    schedule = Schedule()

    args = parse_arguments()
    base_dir = args.base_dir
    threads = list()

    kwargs = {
        'host': '0.0.0.0',
        'port': 5000,
        'threaded': True,
        'use_reloader': False,
        'debug': False,
    }
    flask_thread = Thread(target=app.run, daemon=True, kwargs=kwargs)
    threads.append(flask_thread)
    download_loop_thread = Thread(target=download_loop)
    threads.append(download_loop_thread)

    # running threads
    for thread in threads:
        # print('Thread:', thread)
        thread.start()

    # wait for exit
    answer = input('Quit?')
    if answer.lower() == 'y':
        exit_download_loop = True
        print('exit')

    # cleanup
    for thread in threads:
        thread.join()


if __name__ == '__main__':
    main()
