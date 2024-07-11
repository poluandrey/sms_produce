from django.contrib import admin
from django_admin_inline_paginator.admin import TabularInlinePaginated

from sms.forms import AddBroadcastForm
from sms.models import Broadcast, Sender, Text, Prefix


class SenderAdmin(admin.ModelAdmin):
    pass


class TextAdmin(admin.ModelAdmin):
    pass


class PrefixAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'prefix',
        'broadcast'
    ]


class PrefixInline(TabularInlinePaginated):
    model = Prefix
    extra = 0
    per_page = 10


class BroadcastAdmin(admin.ModelAdmin):
    create_form = AddBroadcastForm
    readonly_fields = ['run_count', 'sent_sms']
    inlines = [PrefixInline]

    list_display = [
        'id',
        'name',
        'comment',
        'is_active',
        'total_sms_count',
        'start_date',
        'end_date',
        'run_count',
        'sent_sms',
    ]

    def get_form(self, request, obj=None, change=False, **kwargs):
        if not obj:
            return self.create_form
        return super(BroadcastAdmin, self).get_form(request, obj, **kwargs)

    def save_related(self, request, form, formsets, change):
        prefixes = form.cleaned_data.get('prefixes')

        if prefixes:
            for prefix in prefixes:
                Prefix.objects.create(broadcast=form.instance, prefix=prefix)
        super(BroadcastAdmin, self).save_related(request, form, formsets, change)

    class Media:
        css = {
            'all': ('css/custom_admin.css',)  # Include extra css
        }


admin.site.register(Sender, SenderAdmin)
admin.site.register(Text, TextAdmin)
admin.site.register(Broadcast, BroadcastAdmin)
admin.site.register(Prefix, PrefixAdmin)