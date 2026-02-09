# İş kaydı istasyon sayım ekranı — Admin içinde

## Kapsam

**Tüm işlemler Django admin (Unfold) içinde yapılacak.** Ekran, `FacilityAdmin` özel sayfası (`get_urls` + `stations_view` + `admin/core/facility/stations.html`) gibi **WorkRecordAdmin** için açılacak özel bir admin sayfası olacak. Uygulama tarafında ayrı URL yok.

## Mevcut yapı (özet)

- **core/models.py**: `Station.benzersiz_kod` = `customer.kod-facility.kod-zone.kod-station.kod`. `WorkRecordStationCount`: work_record, station, sayim_degeri, not_alani. `WorkRecord.bitis_saati` (null ise sayım açık).
- **core/admin.py**: `FacilityAdmin` içinde `get_urls()` ile `<path:object_id>/stations/` ve `stations_view`; şablon `admin/core/facility/stations.html`. Aynı desen WorkRecord için uygulanacak.

## Hedef davranış

| Özellik | Açıklama |
|--------|-----------|
| Konum | Admin: `/admin/core/workrecord/<id>/istasyon-sayim/`. İş kaydı change/list sayfasından link. |
| QR / giriş | Benzersiz kod (QR okutma veya manuel) → Station bulunur; sayı (+ not) girilir; `WorkRecordStationCount` kaydedilir. |
| Özet | Tesis ve bölge bazında toplam istasyon sayısı ile bu iş kaydında girilmemiş (kalan) sayı. Bağlam: `kapatilan_talep.facility` veya sayfada seçilen tesis. |
| Modlar | Aynı sayfada: **Tek giriş** (QR/manuel kod + sayı) ve **Toplu liste** (tesis/bölgeye göre listeleme, sayı girişi/güncelleme). |
| Kilit | `WorkRecord.bitis_saati` doluysa ekleme/düzenleme yok; sadece görüntüleme. |
| Renklendirme | Giriş yapılmış / yapılmamış satırlar (isteğe bağlı). |

## Teknik tasarım (Admin)

### 1. URL ve yetki

- **WorkRecordAdmin.get_urls()** içinde:
  - `path("<path:object_id>/istasyon-sayim/", self.admin_site.admin_view(self.istasyon_sayim_view), name="core_workrecord_istasyon_sayim")`
- `istasyon_sayim_view(request, object_id)`: `get_object_or_404(WorkRecord, pk=object_id)` ve `has_change_permission` (görüntüleme için `has_view_permission`) kontrolü.

### 2. Ana view: `istasyon_sayim_view`

- **GET**: WorkRecord, `locked = (work_record.bitis_saati is not None)`, tesis/bölge bağlamı (kapatilan_talep.facility veya seçilen facility_id), özet (tesis/bölge toplam, girilen, kalan).
- **POST** (kaydet/güncelle): `locked` ise 403; değilse station_id + sayim_degeri (+ not_alani) ile `WorkRecordStationCount` get_or_create/update; redirect veya HTMX parça.
- Lookup: Aynı view’da `?benzersiz_kod=...` veya aynı object_id altında ek path ile Station döndürme (JSON veya HTML parçası).

### 3. Şablon

- Unfold/admin uyumlu: `templates/admin/core/workrecord/istasyon_sayim.html`.
- Admin base extend (`unfold/base.html` veya proje Unfold yapısına göre).
- İçerik: İş kaydı özeti, kilit uyarısı, tesis/bölge özeti, Tek giriş (benzersiz kod + sayı + Kaydet), Toplu liste (tesis/bölge seçimi, tablo, kilit yoksa input + kaydet), renklendirme.

### 4. Admin’de erişim

- İş kaydı change sayfasında “İstasyon sayımı” linki: `reverse('admin:core_workrecord_istasyon_sayim', args=[obj.pk])` (extra_context veya change form şablonu).
- İsteğe list_display’de “İstasyon sayımı” sütunu.

## Dosya değişiklikleri

| Dosya | Değişiklik |
|-------|------------|
| core/admin.py | WorkRecordAdmin: `get_urls()` (istasyon-sayim/), `istasyon_sayim_view`; lookup/save aynı view’da; change/list’te link. |
| templates/admin/core/workrecord/istasyon_sayim.html | Yeni: Özet, kilit, tek giriş, toplu liste; Unfold admin base. |

- config/urls.py veya core/views.py’e bu ekran için **yeni URL/view eklenmeyecek**.

## Uygulama sırası

1. WorkRecordAdmin.get_urls ve istasyon_sayim_view (GET: work_record, locked, özet; tesis bağlamı kapatilan_talep’ten).
2. Lookup: benzersiz_kod → Station (aynı view’da parametre veya alt path).
3. Kaydet: POST ile WorkRecordStationCount (kilit kontrolü).
4. Şablon: admin base, özet, kilit, tek giriş (manuel benzersiz kod + sayı).
5. Toplu liste: tesis/bölge seçimi, tablo, kaydet.
6. İş kaydı change/list’ten “İstasyon sayımı” linki.
7. İsteğe QR kamera (JS); renklendirme.
