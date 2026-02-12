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
    customer_list,
    customer_create,
    customer_edit,
    facility_list,
    facility_create,
    facility_edit,
    facility_add_zone,
    zone_add_station,
    facility_contacts,
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
    path("musteriler/", customer_list, name="customer_list"),
    path("musteriler/ekle/", customer_create, name="customer_create"),
    path("musteriler/<int:pk>/duzenle/", customer_edit, name="customer_edit"),
    path("tesisler/", facility_list, name="facility_list"),
    path("tesisler/ekle/", facility_create, name="facility_create"),
    path("tesisler/<int:pk>/duzenle/", facility_edit, name="facility_edit"),
    path("tesisler/<int:facility_pk>/bolge-ekle/", facility_add_zone, name="facility_add_zone"),
    path("bolgeler/<int:zone_pk>/istasyon-ekle/", zone_add_station, name="zone_add_station"),
    path("musteriler/<int:customer_pk>/tesis/<int:facility_pk>/iletisim/", facility_contacts, name="facility_contacts"),
    path("admin/", admin.site.urls),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
