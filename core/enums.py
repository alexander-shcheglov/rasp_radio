# coding: utf-8

import enum


class Command(enum.Enum):
    PLAY = 'play'
    STOP = 'stop'
    NEXT = 'next'
    PREV = 'previous'
    RAND = 'random'
    VOL_UP = 'volume_up'
    VOL_DOWN = 'volume_down'


class MessageType(enum.Enum):
    COMMAND = 'command'
    NOTIFICATION = 'notification'
    ERROR = 'error'
