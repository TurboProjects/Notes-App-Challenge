from django.contrib import admin
from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')
    list_filter = ()
    search_fields = ('name',)
    ordering = ('name',)
