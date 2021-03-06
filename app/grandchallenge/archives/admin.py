from django.contrib import admin

from grandchallenge.archives.models import Archive, ArchivePermissionRequest


class ArchiveAdmin(admin.ModelAdmin):
    search_fields = ("title",)
    readonly_fields = ("images",)


admin.site.register(Archive, ArchiveAdmin)
admin.site.register(ArchivePermissionRequest)
