from django.contrib import admin
from django_admin_inline_paginator.admin import TabularInlinePaginated
from django.db import transaction


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
    per_page = 20


# class BroadcastAdmin(admin.ModelAdmin):
#     form = AddBroadcastForm
#     readonly_fields = ['run_count', 'sent_sms']
#     inlines = [PrefixInline]
#
#     list_display = [
#         'id',
#         'name',
#         'comment',
#         'is_active',
#         'total_sms_count',
#         'start_date',
#         'end_date',
#         'run_count',
#         'sent_sms',
#     ]
#
#     def save_related(self, request, form, formsets, change):
#         prefixes = form.cleaned_data.get('prefixes')
#
#         if prefixes:
#             for prefix in prefixes:
#                 Prefix.objects.create(broadcast=form.instance, prefix=prefix)
#
#         super(BroadcastAdmin, self).save_related(request, form, formsets, change)
#
#     class Media:
#         css = {
#             'all': ('css/custom_admin.css',)  # Include extra css
#         }
def _chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


class BroadcastAdmin(admin.ModelAdmin):
    form = AddBroadcastForm
    readonly_fields = ['run_count', 'sent_sms']
    inlines = [PrefixInline]

    list_display = [
        'id', 'name', 'comment', 'is_active', 'total_sms_count',
        'start_date', 'end_date', 'run_count', 'sent_sms',
    ]

    fieldsets = (
        (None, {
            'fields': (
                'name', 'comment', 'is_active',
                'phone_number_length', 'total_sms_count',
                'start_date', 'end_date',
                'channel_login', 'channel_password',
                'sender', 'text',
                'run_count', 'sent_sms',
                'prefix_file',        # <-- файл будет виден в админке
            )
        }),
    )

    @transaction.atomic
    def save_related(self, request, form, formsets, change):
        # сначала обычное сохранение M2M/inline
        super().save_related(request, form, formsets, change)

        prefixes = getattr(form, 'parsed_prefixes', []) or []
        if not prefixes:
            return

        broadcast = form.instance

        # уже существующие префиксы этой рассылки (чтобы не плодить дубликаты)
        existing = set(
            Prefix.objects.filter(broadcast=broadcast, prefix__in=prefixes)
                          .values_list('prefix', flat=True)
        )

        to_create = [Prefix(broadcast=broadcast, prefix=p)
                     for p in prefixes if p not in existing]

        # крупными партиями — быстрее и экономнее по памяти
        for chunk in _chunked(to_create, 5000):
            Prefix.objects.bulk_create(chunk, ignore_conflicts=True)

        # self.message_user(request, f'Загружено префиксов: {len(to_create)} (пропущено существующих: {len(existing)})')

    class Media:
        css = {'all': ('css/custom_admin.css',)}
        

admin.site.register(Sender, SenderAdmin)
admin.site.register(Text, TextAdmin)
admin.site.register(Broadcast, BroadcastAdmin)
admin.site.register(Prefix, PrefixAdmin)
