"""
Admin ana sayfa (dashboard) için veri sağlayan callback. UNFOLD DASHBOARD_CALLBACK ile kullanılır.
"""
from datetime import date
from django.urls import reverse


def admin_dashboard_callback(request, context):
    """Dashboard için özet sayılar ve son kayıtları context'e ekler."""
    try:
        from django.db.models import Count
        from django.utils import timezone
        from core.models import Customer, Facility, Talep, WorkRecord

        # Özet sayılar (yetki filtrelemesi yok; staff görür)
        musteri_count = Customer.objects.count()
        tesis_count = Facility.objects.count()
        talep_bekleyen = Talep.objects.exclude(durum="yapildi").count()
        bugun = timezone.now().date()
        ay_basi = bugun.replace(day=1)
        is_kaydi_ay = WorkRecord.objects.filter(tarih__gte=ay_basi, tarih__lte=bugun).count()

        context["dashboard_stats"] = {
            "musteri_count": musteri_count,
            "tesis_count": tesis_count,
            "talep_bekleyen": talep_bekleyen,
            "is_kaydi_ay": is_kaydi_ay,
        }

        # Son iş kayıtları (en son 8)
        recent_wr = list(
            WorkRecord.objects.select_related("personel", "ekip", "kapatilan_talep")
            .order_by("-tarih", "-created_at")[:8]
        )
        context["dashboard_recent_work_records"] = []
        for wr in recent_wr:
            context["dashboard_recent_work_records"].append({
                "pk": wr.pk,
                "tarih": wr.tarih,
                "form_numarasi": wr.form_numarasi or f"#{wr.pk}",
                "personel": wr.personel.get_username() if wr.personel_id else "—",
                "ekip": str(wr.ekip) if wr.ekip_id else "—",
                "url": reverse("admin:core_workrecord_change", args=[wr.pk]) if request.user.has_perm("core.change_workrecord") else None,
            })

        # Bekleyen / planlanan talepler (en son 8)
        open_talepler = list(
            Talep.objects.filter(durum__in=("beklemede", "planlandi"))
            .select_related("customer", "facility", "tip")
            .order_by("-tarih", "-created_at")[:8]
        )
        context["dashboard_open_talepler"] = []
        for t in open_talepler:
            context["dashboard_open_talepler"].append({
                "pk": t.pk,
                "tarih": t.tarih,
                "durum": t.get_durum_display(),
                "customer": str(t.customer) if t.customer_id else "—",
                "tip": str(t.tip) if t.tip_id else "—",
                "url": reverse("admin:core_talep_change", args=[t.pk]) if request.user.has_perm("core.change_talep") else None,
            })

    except Exception:
        context.setdefault("dashboard_stats", {})
        context.setdefault("dashboard_recent_work_records", [])
        context.setdefault("dashboard_open_talepler", [])
    return context
