from django.contrib import admin
from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'published', 'created_at']
    list_filter = ['published']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = [
        ('Content', {
            'fields': ['title', 'slug', 'meta_description', 'content', 'published']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
        }),
    ]
    readonly_fields = ['created_at', 'updated_at']