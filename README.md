# Kale İlaçlama

Kale İlaçlama için geliştirilen web uygulaması. Müşteri ve tesis kayıtları, tesis içi bölge ve istasyon yönetimi, talep (şikayet / yapılacaklar) takibi ve iş kayıtları ile istasyon sayım bilgilerinin tutulması amacıyla kullanılır.

## Amaç

- **Müşteri ve tesis yönetimi:** Müşteriler ve müşterilere ait tesisler kayıt altına alınır.
- **Bölge ve istasyon:** Her tesiste bölgeler tanımlanır; bölgelerde yerleştirilen istasyonlar için yer bilgisi girilir.
- **Talep yönetimi:** Müşteri isteği veya periyodik talep listesi ile oluşturulan talepler (şikayet / yapılacaklar) tarih etiketli tutulur; hangi iş kaydı ile kapatıldığı takip edilir.
- **İş kaydı:** Tarih etiketli iş kayıtlarında uygulamalar, istasyonlardan alınan sayım bilgileri ve personel (kullanıcı) bilgisi girilir; talepler bu iş kayıtları ile kapatılır.

## Varlıklar

| Varlık | Açıklama |
|--------|----------|
| **Müşteri (Customer)** | Kısa kodu olan müşteri kaydı. |
| **Tesis (Facility)** | Müşteriye ait tesis; kısa kodu vardır. |
| **Bölge (Zone)** | Tesise ait bölge; kısa kodu vardır. |
| **İstasyon (Station)** | Bölgede konumlanan istasyon; yer bilgisi ve benzersiz kodu vardır. |
| **Talep (Request)** | Tarih etiketli talep (şikayet veya yapılacak); hangi iş kaydı ile kapatıldığı takip edilir. |
| **İş kaydı (WorkRecord)** | Tarih, personel (User), uygulamalar ve istasyon sayım bilgilerini içerir; talepleri kapatır. |

## Kodlama kuralları

- **Müşteri kodu:** Kısa kod (örn. `M1`, `M2`). Müşteri bazında tekil.
- **Tesis kodu:** Kısa kod (örn. `T1`, `T2`). Aynı müşteriye ait tesisler içinde tekil.
- **Bölge kodu:** Kısa kod (örn. `B1`, `B2`). Aynı tesis içinde tekil.
- **İstasyon benzersiz kodu:**  
  `müşteri_kodu` + `-` + `tesis_kodu` + `-` + `bölge_kodu` + `-` + **sayaç**  
  Sayaç, ilgili bölgedeki istasyon sıra numarasıdır (örn. `001`, `002`).  
  Örnek: `M1-T1-B1-001`, `M1-T1-B1-002`.

## Teknoloji

- **Backend:** Django  
- **Veritabanı:** SQLite  
- **Ayarlar:** `config` paketi (`config/settings.py`)  
- **Frontend:** Django template yapısı (ayrı frontend projesi yok; sunucu kurulumu tek proje ile kolay)
- **CSS:** Tailwind CSS (CDN ile; istenirse build pipeline eklenebilir)
- **Etkileşim:** HTMX ile sayfa parçası güncellemeleri ve form davranışları

## Proje yapısı

- `config/` – Django ayarları (settings, urls, wsgi, asgi)
- `core/` – Ana uygulama (modeller, admin, view’lar; ileride tasarım/mimariye göre genişletilecek)
- `templates/` – Genel şablonlar (`base.html`: Tailwind + HTMX)
- `manage.py` – Django yönetim komutu

## Çalıştırma

```bash
# Sanal ortamı etkinleştir (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Sunucuyu başlat
py manage.py runserver
```

Yönetim paneli: `/admin/` (önce `py manage.py createsuperuser` ile süper kullanıcı oluşturun).

Tasarım ve mimari dokümanı ileride eklenecektir.
