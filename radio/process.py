# coding: utf-8

import gi
gi.require_version('Gst', '1.0')

from gi.repository import GLib, Gst, GObject

from threading import Thread

from core.enums import MessageType, Command
from core.server import CommandServer
from .models import Radio

MAX_VOLUME = 1.0
MIN_VOLUME = 0.0

VOL_PROPERTY = 'volume'
VOL_UP = 'volume_up'
VOL_DOWN = 'volume_down'


class RadioThread(Thread):
    def __init__(self, uri=None, callback=None, *args, **kwargs):
        Thread.__init__(self, *args, **kwargs)
        self.uri = uri
        self.loop = None
        self.uri = uri
        self.playbin = None
        self.volume_step = 0.05
        self.volume_level = 0.5
        self.stats = {'volume': self.volume_level}
        self.callback = callback

    def set_volume(self, level=MAX_VOLUME):
        self.volume_level = level if MIN_VOLUME <= level <= MAX_VOLUME else self.volume_level
        self.playbin.set_property(VOL_PROPERTY, self.volume_level)

    def notify(self, message=None):
        notification = (
            MessageType.NOTIFICATION.value,
            message,
            self.stats
        )
        self.callback(notification)

    def volume_up(self):
        self.set_volume(self.volume_level + self.volume_step)
        self.stats.update({'volume': self.volume_level})
        self.notify()

    def volume_down(self):
        self.set_volume(self.volume_level - self.volume_step)
        self.stats.update({'volume': self.volume_level})
        self.notify()

    def run(self):
        self.playbin = Gst.ElementFactory.make("playbin", None)

        if self.playbin:
            if Gst.uri_is_valid(self.uri):
                uri = self.uri
            else:
                uri = Gst.filename_to_uri(self.uri)
            self.playbin.set_property('uri', uri)
            self.playbin.set_property('volume', self.volume_level)

            bus = self.playbin.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self.bus_call, self.loop)
            bus.connect("message::tag", self.on_tag)

            self.playbin.set_state(Gst.State.PLAYING)
            self.loop = GLib.MainLoop()
            try:
                self.stats.update(dict(status='playing'))
                self.notify()
                self.loop.run()
            except OSError as e:
                pass
            finally:
                self.loop.quit()
                self.playbin.set_state(Gst.State.NULL)
                self.stats.update(dict(status='stopped'))
                self.notify()

    def on_tag(self, bus, msg):
        if msg.type == Gst.MessageType.TAG:
            struct = msg.get_structure()
            taglist = struct.get_value('taglist')
            tags = (
                [
                    (
                        taglist.nth_tag_name(x),
                        taglist.get_string(taglist.nth_tag_name(x))[1]
                    ) for x in range(taglist.n_tags())
                ]
            )
            self.stats.update(tags)
            self.notify()

    def bus_call(self, bus, msg, loop):
        t = msg.type
        if t == Gst.MessageType.EOS:
            self.loop.quit()
        elif t == Gst.MessageType.ERROR:
            self.loop.quit()
        return True


class RadioProcess(CommandServer):

    def __init__(self, server_address=None, *args, **kwargs):
        super().__init__(server_address)
        GObject.threads_init()
        Gst.init(None)
        self.radio_thread = None
        self.current_station = None

    def process_command(self, command):
        _, method, kwargs = command
        try:
            getattr(self, Command(method).value)(**kwargs)
        except (AttributeError, ValueError) as e:
            self.notify(
                (MessageType.NOTIFICATION, 'Wrong command: {}'.format(method), {})
            )

    def start_radio_thread(self):
        if not self.radio_thread or not self.radio_thread.is_alive():
            del self.radio_thread
            self.radio_thread = None
            if self.current_station.first_source:
                self.radio_thread = RadioThread(self.current_station.first_source.path, self.notify)
                self.radio_thread.start()

    def volume_up(self):
        if self.radio_thread and self.radio_thread.is_alive():
            self.radio_thread.volume_up()

    def volume_down(self):
        if self.radio_thread and self.radio_thread.is_alive():
            self.radio_thread.volume_down()

    def set_station(self, next=False, previous=False, random=False):
        if not self.current_station:
            self.current_station = Radio.get_random()
        else:
            another_station = None
            if next:
                another_station = self.current_station.get_next() or self.current_station.get_previous()
            if previous:
                another_station = self.current_station.get_previous() or self.current_station.get_next()
            if random:
                another_station = Radio.get_random()
            self.current_station = another_station or self.current_station
        self.restart_radio_thread()

    def stop(self):
        if self.radio_thread and self.radio_thread.is_alive():
            self.radio_thread.loop.quit()
            self.radio_thread = None

    def restart_radio_thread(self):
        self.stop()
        self.start_radio_thread()

    def random(self):
        self.set_station(random=True)

    def next(self):
        self.set_station(next=True)

    def previous(self):
        self.set_station(previous=True)

    def play(self):
        if not self.current_station:
            self.current_station = Radio.get_random()
        self.start_radio_thread()
