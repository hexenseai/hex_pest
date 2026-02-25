"""URL configuration for config project."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from core.reports import ilac_kullanımlari_raporu, istasyon_raporu
from core.views import (
    home,
    login_view,
    logout_view,
    service_worker,
    client_facility_list,
    client_work_record_list,
    client_istasyon_raporu,
    client_bagimsiz_tespit_list,
)

admin.site.site_header = "Kale İlaçlama Yönetim Paneli"
admin.site.site_title = "Kale İlaçlama"
admin.site.index_title = "Yönetim Paneli"


def _admin_extra_urls():
    return [
        path(
            "raporlar/ilac-kullanımlari/",
            admin.site.admin_view(ilac_kullanımlari_raporu),
            name="rapor_ilac_kullanımlari",
        ),
        path(
            "raporlar/istasyon-raporu/",
            admin.site.admin_view(istasyon_raporu),
            name="rapor_istasyon",
        ),
    ]


admin.site.extra_urls = _admin_extra_urls

urlpatterns = [
    path("service-worker.js", service_worker, name="service_worker"),
    path("", home, name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("tesisler/", client_facility_list, name="client_facility_list"),
    path("faaliyet-kayitlari/", client_work_record_list, name="client_work_record_list"),
    path("istasyon-raporu/", client_istasyon_raporu, name="client_istasyon_raporu"),
    path("bagimsiz-tespitler/", client_bagimsiz_tespit_list, name="client_bagimsiz_tespit_list"),
    path("admin/", admin.site.urls),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
