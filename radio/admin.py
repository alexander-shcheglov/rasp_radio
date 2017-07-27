# coding: utf-8

from django.contrib import admin
from .models import Radio, SourceUri


class SourceUriAdmin(admin.TabularInline):
    model = SourceUri


class RadioAdmin(admin.ModelAdmin):
    inlines = (SourceUriAdmin,)


admin.site.register(Radio, RadioAdmin)
