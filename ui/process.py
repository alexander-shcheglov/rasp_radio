# coding: utf-8

import logging
import os
import pickle
import socket
import sys

import pygameui as ui

from core.enums import MessageType, Command

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
log_format = '%(asctime)-6s: %(name)s - %(levelname)s - %(message)s'
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(log_format))
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)


screen_size = (480, 320)

TITLES_WIDTH = 100
LABEL_HEIGHT = 30
MARGIN = 5
BUTTON_WIDTH = 70
BUTTON_HEIGHT = 40
BUTTON_MARGIN = 8
LABEL_MASK = 'label_{}'
BUTTON_MASK = 'button_{}'
BUTTON_CLICK_MASK = 'click_{}'


def create_rect(x=MARGIN, y=None, width=TITLES_WIDTH, height=LABEL_HEIGHT):
    return ui.Rect(
        x, y, width, height
    )


def get_text(x):
    if isinstance(x, str):
        return x
    elif isinstance(x, float):
        return '{:.2f}'.format(x)


class RadioScene(ui.Scene):
    def __init__(
            self,
            socket_address
    ):
        super().__init__()
        self.socket_address = socket_address
        self.playing = False
        self.set_ui()
        self.sock = None

    def close_socket(self):
        self.sock.close()
        self.sock = None

    def create_socket(self):
        if not self.sock:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.sock.connect(self.socket_address)
                self.sock.setblocking(False)
            except OSError:
                self.close_socket()

    def notify(self, message=None):
            self.create_socket()
            if message and self.sock:
                try:
                    self.sock.sendall(pickle.dumps(message))
                except OSError:
                    self.close_socket()

    def read_notification(self):
        try:
            self.create_socket()
            data = self.sock.recv(1024)
            if data:
                return pickle.loads(data)
        except BlockingIOError:
            pass
        except (OSError, pickle.UnpicklingError, EOFError) as e:
            self.close_socket()
        return None

    def set_ui(self):

        titles = ['Organization', 'Genre', 'Title', 'Status', 'Volume']
        [self.add_child(
            ui.Label(
                create_rect(y=MARGIN + i * LABEL_HEIGHT),
                '{} :'.format(x),
                halign=ui.RIGHT
            )
        ) for i, x in enumerate(titles)]
        for i, x in enumerate(titles):
            setattr(self, LABEL_MASK.format(x.lower()), ui.Label(
                create_rect(
                    MARGIN * 2 + TITLES_WIDTH,
                    MARGIN + i * LABEL_HEIGHT,
                    TITLES_WIDTH * 2),
                'some_text_{}'.format(x.lower()),
                halign=ui.LEFT
            ))
            self.add_child(getattr(self, LABEL_MASK.format(x.lower())))

        buttons = ['Previous', 'Play', 'Next', 'Random', 'VolDown', 'VolUp']
        for i, x in enumerate(buttons):
            x_coord = BUTTON_MARGIN+(BUTTON_WIDTH+BUTTON_MARGIN) * i
            setattr(self, BUTTON_MASK.format(x.lower()), ui.Button(
                create_rect(
                    x=x_coord,
                    y=250,
                    width=BUTTON_WIDTH,
                    height=BUTTON_HEIGHT),
                x)
            )
            button = getattr(self, BUTTON_MASK.format(x.lower()))
            button.on_clicked.connect(
                getattr(self, BUTTON_CLICK_MASK.format(x.lower())))
            self.add_child(button)
        self.set_playing()

    def set_playing(self, playing=False):
        text = 'Stop' if playing else 'Play'
        button = getattr(self, BUTTON_MASK.format('play'))
        button._text = text
        button.stylize()
        button.render()
        self.playing = playing

    def click_previous(self, *args, **kwargs):
        self.notify((MessageType.COMMAND.value, Command.PREV.value, {}))
        self.set_playing(True)

    def click_play(self, *args, **kwargs):
        if self.playing:
            self.notify((MessageType.COMMAND.value, Command.STOP.value, {}))
            self.set_playing(False)
        else:
            self.notify((MessageType.COMMAND.value, Command.PLAY.value, {}))
            self.set_playing(True)

    def click_next(self, *args, **kwargs):
        self.notify((MessageType.COMMAND.value, Command.NEXT.value, {}))
        self.set_playing(True)

    def click_random(self, *args, **kwargs):
        self.notify((MessageType.COMMAND.value, Command.RAND.value, {}))
        self.set_playing(True)

    def click_volup(self, *args, **kwargs):
        self.notify((MessageType.COMMAND.value, Command.VOL_UP.value, {}))

    def click_voldown(self, *args, **kwargs):
        self.notify((MessageType.COMMAND.value, Command.VOL_DOWN.value, {}))

    def update(self, dt):
        notification = self.read_notification()
        if notification:
            params = notification[2]
            for key in params.keys():
                try:
                    text = get_text(params[key])
                    getattr(self, LABEL_MASK.format(key)).text = text
                    if key == 'status':
                        self.set_playing(text == 'playing')
                except AttributeError:
                    pass
        super().update(dt)


class RadioUIProcess(object):

    def __init__(self, socket_address, config):
        ui.init('pygameui - Kitchen Sink', config=config)
        ui.scene.push(RadioScene(socket_address))
        ui.run()

