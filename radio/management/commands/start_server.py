# coding: utf-8

from django.core.management.base import BaseCommand
from django.conf import settings

from radio.process import RadioProcess


class Command(BaseCommand):

    help = 'starts socket server'

    def handle(self, *args, **options):

        server = RadioProcess(settings.SERVER_ADDRESS)
        server.loop()

