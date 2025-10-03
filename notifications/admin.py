from django.contrib import admin

from notifications.models import UserProfile
from django.contrib.auth.admin import UserAdmin

# Register your models here.
@admin.register(UserProfile)
class UserProfile(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'telegram_chat_id')