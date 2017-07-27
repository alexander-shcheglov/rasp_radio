# coding: utf-8

# coding: utf-8

from django.core.management.base import BaseCommand
from django.conf import settings

from ui.process import RadioUIProcess


class Command(BaseCommand):

    help = 'starts ui'

    def handle(self, *args, **options):

        ui = RadioUIProcess(settings.SERVER_ADDRESS, settings.PYGAME_CONFIG)


