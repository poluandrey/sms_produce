from django.contrib import admin

from sms.models import Broadcast, Sender, Text


class SenderAdmin(admin.ModelAdmin):
    pass


class TextAdmin(admin.ModelAdmin):
    pass


class BroadcastAdmin(admin.ModelAdmin):
    readonly_fields = ['run_count']
    list_display = [
        'id',
        'name',
        'comment',
        'is_active',
        'prefix',
        'total_sms_count',
        'start_date',
        'end_date',
        'channel_login',
        'channel_password',
        'run_count',
        'sent_sms',
    ]


admin.site.register(Sender, SenderAdmin)
admin.site.register(Text, TextAdmin)
admin.site.register(Broadcast, BroadcastAdmin)
