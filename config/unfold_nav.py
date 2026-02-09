"""Unfold admin sidebar: Admin paneli gruplama yapısı ile aynı (app listesi + yetkiye göre gizleme)."""

from django.contrib import admin
from django.urls import reverse

# Çekirdek (core) uygulaması menüde üç grup olarak gösterilir
CORE_NAV_GROUPS = {
    "Müşteri Yönetimi": [
        "core.customer",
        "core.facility",
        "core.zone",
        "core.station",
        "core.periyod",
    ],
    "Faaliyet Yönetimi": [
        "core.workrecord",
        "core.talep",
        "core.workrecordstationcount",
    ],
    "Sistem": [
        "core.ekip",
        "core.taleptipi",
        "core.uygulamatanim",
        "core.faaliyettanim",
        "core.ilactanim",
        "core.tespittanim",
    ],
}

# Nav bar öğeleri için Material Symbols ikon adları (https://fonts.google.com/icons)
CORE_NAV_ICONS = {
    "core.customer": "people",
    "core.facility": "business",
    "core.zone": "map",
    "core.station": "qr_code_2",
    "core.periyod": "event_repeat",
    "core.workrecord": "assignment",
    "core.talep": "support_agent",
    "core.workrecordstationcount": "qr_code_scanner",
    "core.ekip": "groups",
    "core.taleptipi": "label",
    "core.uygulamatanim": "science",
    "core.faaliyettanim": "build_circle",
    "core.ilactanim": "medication",
    "core.tespittanim": "bug_report",
}


def _model_label(model_dict):
    """Model dict'ten app_label.model_name döner (küçük harf)."""
    m = model_dict.get("model")
    if m is None:
        return None
    return m._meta.label_lower


def get_sidebar_navigation(request):
    """
    Sol menüyü admin panelinin app/model yapısından üretir.
    - Çekirdek (core) uygulaması: "Müşteri Yönetimi", "Faaliyet Yönetimi", "Sistem" olarak üç grup.
    - Diğer uygulamalar: AppConfig.verbose_name ile tek grup.
    - Öğeler = Kullanıcının yetkisi olan modeller. Yetkisi kaldırılanlar menüde görünmez.
    """
    app_list = admin.site.get_app_list(request)
    navigation = []

    for app in app_list:
        app_label = app.get("app_label", "")
        models_with_url = [
            m for m in app["models"]
            if m.get("admin_url")
        ]

        if app_label == "core":
            # Çekirdek: iki ayrı grup; öğe sırası CORE_NAV_GROUPS listesine göre
            for group_title, allowed_labels in CORE_NAV_GROUPS.items():
                by_label = {
                    _model_label(m): m for m in models_with_url
                    if _model_label(m)
                }
                items = []
                for label in allowed_labels:
                    model = by_label.get(label.lower())
                    if model and model.get("admin_url"):
                        label_key = label.lower()
                        items.append({
                            "title": model["name"],
                            "link": model["admin_url"],
                            "icon": CORE_NAV_ICONS.get(label_key),
                        })
                if items:
                    navigation.append({
                        "title": group_title,
                        "collapsible": True,
                        "items": items,
                    })
            continue

        # Diğer uygulamalar: tek grup (app adı)
        items = []
        for model in models_with_url:
            label = _model_label(model)
            items.append({
                "title": model["name"],
                "link": model["admin_url"],
                "icon": CORE_NAV_ICONS.get(label) if label else None,
            })
        if items:
            navigation.append({
                "title": app["name"],
                "collapsible": True,
                "items": items,
            })

    # Raporlar grubu (admin ek URL'leri + faaliyet raporları listesi)
    navigation.append({
        "title": "Raporlar",
        "collapsible": True,
        "items": [
            {
                "title": "İlaç Kullanımları",
                "link": reverse("admin:rapor_ilac_kullanımlari"),
                "icon": "medication",
            },
            {
                "title": "Faaliyet Raporları",
                "link": reverse("admin:core_faaliyetraporu_changelist"),
                "icon": "picture_as_pdf",
            },
            {
                "title": "İstasyon Raporu",
                "link": reverse("admin:rapor_istasyon"),
                "icon": "table_chart",
            },
        ],
    })

    return navigation
