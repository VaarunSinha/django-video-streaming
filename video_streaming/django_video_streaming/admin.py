from django.contrib import admin

# Register your models here.
from .models import Segment, DjangoStreamVideo

admin.site.register(Segment)
admin.site.register(DjangoStreamVideo)
