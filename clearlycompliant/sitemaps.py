from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return ['checkout', 'privacy_policy', 'terms_and_conditions']

    def location(self, item):
        return reverse(item)