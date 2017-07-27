# coding: utf-8

from django.db import models


class Radio(models.Model):
    title = models.TextField(null=False, verbose_name='Radio Title')
    url = models.TextField(default='', verbose_name='Radio Url')

    class Meta:
        verbose_name = 'radio'
        verbose_name_plural = 'radios'

    def __str__(self):
        return self.title

    def get_another(self, previous=False):
        _filter = {'id__{}'.format('lt' if previous else 'gt'): self.id}
        return self.__class__.objects.filter(**_filter).order_by('id').first()

    def get_next(self):
        return self.get_another()

    def get_previous(self):
        return self.get_another(True)

    @property
    def first_source(self):
        return self.sources.first()

    @classmethod
    def get_random(cls):
        return cls.objects.order_by('?').first()


class SourceUri(models.Model):
    path = models.TextField(null=False, verbose_name='Uri path')
    radio = models.ForeignKey(Radio, related_name='sources')

    class Meta:
        verbose_name = 'source'
        verbose_name_plural = 'sources'

    def __str__(self):
        return self.path

