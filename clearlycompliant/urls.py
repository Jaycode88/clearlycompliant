from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from django.http import FileResponse
from django.conf import settings
import os
from .sitemaps import StaticViewSitemap, BlogSitemap

sitemap_config = {
    'static': StaticViewSitemap,
    'blog': BlogSitemap,
}


def serve_llms_txt(request):
    llms_path = os.path.join(settings.BASE_DIR, 'static', 'llms.txt')
    return FileResponse(open(llms_path, 'rb'), content_type='text/plain')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('orders/', include('orders.urls')),
    path('', include('orders.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemap_config}, name='django.contrib.sitemaps.views.sitemap'),
    path('llms.txt', serve_llms_txt),
    path('blog/', include('blog.urls')),
]