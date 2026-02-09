from django.db import models
from django.conf import settings


class UserProfile(models.Model):
    """Kullanıcı profil fotoğrafı ve opsiyonel müşteri bağlantısı (kare, admin'de kırparak yüklenir)."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Kullanıcı",
    )
    customer = models.ForeignKey(
        "Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profiles",
        verbose_name="Geçerli müşteri",
        help_text="Bu kullanıcının bağlı olduğu müşteri (opsiyonel).",
    )
    avatar = models.ImageField(
        "Profil fotoğrafı",
        upload_to="avatars/%Y/%m/",
        blank=True,
        null=True,
        help_text="Kare formatta yükleyin. Yüklemeden önce hizalayıp kırpabilirsiniz.",
    )

    class Meta:
        verbose_name = "Kullanıcı profili"
        verbose_name_plural = "Kullanıcı profilleri"

    def __str__(self):
        return f"{self.user.get_username()} profili"


class Customer(models.Model):
    """Müşteri (firma). Yetkili ve iletişim bilgileri addressbook.Contact ile tutulur."""
    kod = models.CharField("Kod", max_length=20, unique=True)
    firma_ismi = models.CharField("Firma ismi", max_length=200)
    logo = models.ImageField(
        "Logo",
        upload_to="customer_logos/%Y/%m/",
        blank=True,
        null=True,
        help_text="Kare formatta yükleyin. Yüklemeden önce hizalayıp kırpabilirsiniz.",
    )
    adres = models.TextField("Adres", blank=True)
    not_alani = models.TextField("Not", blank=True)
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "Müşteri"
        verbose_name_plural = "Müşteriler"
        ordering = ["kod"]

    def __str__(self):
        return f"{self.kod} - {self.firma_ismi}"


class Facility(models.Model):
    """Tesis (müşteriye ait)."""
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="tesisler",
        verbose_name="Müşteri",
    )
    kod = models.CharField("Kod", max_length=20)
    ad = models.CharField("Tesis adı", max_length=200)
    adres = models.TextField("Adres", blank=True)
    not_alani = models.TextField("Not", blank=True)
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "Tesis"
        verbose_name_plural = "Tesisler"
        ordering = ["customer", "kod"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "kod"],
                name="unique_customer_facility_kod",
            )
        ]

    def __str__(self):
        return f"{self.customer.kod}-{self.kod} {self.ad}"


class Periyod(models.Model):
    """
    Periyodik ziyaret tanımı (takvim tekrarlama). Müşteri/tesis için belirli aralıklarla
    talep kaydı oluşturmak üzere kullanılır.
    """
    SIKLIK_GUNLUK = "gunluk"
    SIKLIK_HAFTALIK = "haftalik"
    SIKLIK_AYLIK = "aylik"
    SIKLIK_YILLIK = "yillik"
    SIKLIK_CHOICES = [
        (SIKLIK_GUNLUK, "Günlük"),
        (SIKLIK_HAFTALIK, "Haftalık"),
        (SIKLIK_AYLIK, "Aylık"),
        (SIKLIK_YILLIK, "Yıllık"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="periyodlar",
        verbose_name="Müşteri",
    )
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="periyodlar",
        verbose_name="Tesis",
        help_text="Boş bırakılırsa müşteri geneli kabul edilebilir.",
    )
    ad = models.CharField("Ad", max_length=200, blank=True, help_text="Tanım adı (isteğe bağlı)")
    talep_tipi = models.ForeignKey(
        "TalepTipi",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="periyodlar",
        verbose_name="Talep tipi",
        help_text="Otomatik oluşturulacak taleplerin tipi. Boş bırakılabilir.",
    )
    baslangic_tarihi = models.DateField("Başlangıç tarihi")
    bitis_tarihi = models.DateField("Bitiş tarihi", null=True, blank=True, help_text="Boşsa süresiz tekrarlanır.")
    tekrar_sayisi = models.PositiveSmallIntegerField(
        "Tekrar sayısı",
        null=True,
        blank=True,
        help_text="Bu kadar oluşturduktan sonra dur. Boşsa bitiş tarihine kadar.",
    )
    siklik = models.CharField(
        "Sıklık",
        max_length=20,
        choices=SIKLIK_CHOICES,
        default=SIKLIK_HAFTALIK,
    )
    aralik = models.PositiveSmallIntegerField(
        "Aralık",
        default=1,
        help_text="Her kaç birimde bir (örn. her 2 hafta için 2).",
    )
    # Haftalık: hangi günler (virgülle ayrılmış 1-7, 1=Pazartesi)
    haftanin_gunleri = models.CharField(
        "Haftanın günleri",
        max_length=50,
        blank=True,
        help_text="Haftalık için: 1=Pzt, 2=Sal, 3=Çar, 4=Per, 5=Cum, 6=Cmt, 7=Paz. Virgülle ayırın (örn. 1,3,5).",
    )
    # Aylık: ayın kaçıncı günü (1-31)
    ayin_gunu = models.PositiveSmallIntegerField(
        "Ayın günü",
        null=True,
        blank=True,
        help_text="Aylık için: 1-31 arası.",
    )
    # Yıllık: ay (1-12)
    ay = models.PositiveSmallIntegerField(
        "Ay",
        null=True,
        blank=True,
        help_text="Yıllık için: 1-12 arası.",
    )
    aktif = models.BooleanField("Aktif", default=True)
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "Periyod"
        verbose_name_plural = "Periyodlar"
        ordering = ["customer", "facility", "baslangic_tarihi"]

    def __str__(self):
        facility_str = f" — {self.facility}" if self.facility_id else ""
        return f"{self.customer.kod}{facility_str} ({self.get_siklik_display()})"


class Zone(models.Model):
    """Bölge (tesise ait)."""
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name="bolgeler",
        verbose_name="Tesis",
    )
    kod = models.CharField("Kod", max_length=20)
    ad = models.CharField("Ad", max_length=200)
    not_alani = models.TextField("Not", blank=True)
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "Bölge"
        verbose_name_plural = "Bölgeler"
        ordering = ["facility", "kod"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "kod"],
                name="unique_facility_zone_kod",
            )
        ]

    def __str__(self):
        return f"{self.facility.customer.kod}-{self.facility.kod}-{self.kod} {self.ad}"


class Station(models.Model):
    """İstasyon (bölgede). Kod kullanıcı girer; benzersiz kod = müşteri-tesis-bölge-istasyon kodları birleşimi."""
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name="istasyonlar",
        verbose_name="Bölge",
    )
    kod = models.CharField("Kod", max_length=20)
    ad = models.CharField("Ad", max_length=150)
    benzersiz_kod = models.CharField(
        "Benzersiz kod",
        max_length=80,
        unique=True,
        blank=True,
        editable=False,
    )
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "İstasyon"
        verbose_name_plural = "İstasyonlar"
        ordering = ["zone", "kod"]
        constraints = [
            models.UniqueConstraint(
                fields=["zone", "kod"],
                name="unique_zone_station_kod",
            )
        ]

    def __str__(self):
        return self.benzersiz_kod or f"({self.pk})"

    def save(self, *args, **kwargs):
        if self.zone_id and self.kod:
            customer = self.zone.facility.customer
            facility = self.zone.facility
            zone = self.zone
            self.benzersiz_kod = (
                f"{customer.kod}-{facility.kod}-{zone.kod}-{self.kod}"
            )
        super().save(*args, **kwargs)


class Ekip(models.Model):
    """Ekip: kod, lider (User), kişi sayısı, üyeler (metin)."""
    kod = models.CharField("Ekip kodu", max_length=20, unique=True)
    ekip_lideri = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lideri_oldugu_ekipler",
        verbose_name="Ekip lideri",
    )
    kisi_sayisi = models.PositiveSmallIntegerField("Ekip kişi sayısı", default=0)
    uyeler = models.TextField("Ekip üyeleri", blank=True, help_text="Üye isimleri veya not (serbest metin)")
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "Ekip"
        verbose_name_plural = "Ekipler"
        ordering = ["kod"]

    def __str__(self):
        return self.kod


class UygulamaTanim(models.Model):
    """Yapılabilecek uygulamaların tanım listesi (metin). İş kaydında yapılan uygulamalar buradan seçilir."""
    ad = models.CharField("Uygulama", max_length=300)
    sira = models.PositiveSmallIntegerField("Sıra", default=0, help_text="Liste sıralaması")
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "Uygulama tanımı"
        verbose_name_plural = "Uygulama tanımları"
        ordering = ["sira", "ad"]

    def __str__(self):
        return self.ad


class FaaliyetTanim(models.Model):
    """Düzeltici / önleyici faaliyet tanım listesi. İş kaydında faaliyet seçilip bayraklar işaretlenir."""
    ad = models.CharField("Faaliyet", max_length=300)
    sira = models.PositiveSmallIntegerField("Sıra", default=0, help_text="Liste sıralaması")
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "Faaliyet tanımı"
        verbose_name_plural = "Faaliyet tanımları"
        ordering = ["sira", "ad"]

    def __str__(self):
        return self.ad


class IlacTanim(models.Model):
    """İlaç / fareyemi tanımı. Temin firması, ticari isim, aktif madde, ambalaj, antidot. Sadece aktif olanlar yeni kayıtta seçilir."""
    temin_edildigi_firma = models.CharField("Temin Edildiği Firma", max_length=150, blank=True)
    ticari_ismi = models.CharField("Ticari İsmi", max_length=150)
    aktif_madde = models.CharField("Aktif Madde", max_length=100, blank=True)
    ambalaj = models.CharField("Ambalaj", max_length=20, blank=True)
    antidot = models.CharField("Antidot", max_length=50, blank=True)
    aktif = models.BooleanField("Aktif", default=True, help_text="Pasif ilaçlar yeni iş kaydında seçilemez; mevcut kayıtlar görünür kalır.")
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "İlaç tanımı"
        verbose_name_plural = "İlaç tanımları"
        ordering = ["ticari_ismi"]

    def __str__(self):
        return self.ticari_ismi or f"İlaç #{self.pk}"


class WorkRecord(models.Model):
    """İş kaydı (tarih, personel, ekip, başlama/bitiş saati, yapılan uygulamalar detayı, öneriler). Bir talep bu kayıtla kapatılır (1-1)."""
    tarih = models.DateField("Tarih")
    personel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="is_kayitlari",
        verbose_name="Personel",
    )
    ekip = models.ForeignKey(
        "Ekip",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="is_kayitlari",
        verbose_name="Ekip",
    )
    baslama_saati = models.TimeField("Başlama saati", null=True, blank=True)
    bitis_saati = models.TimeField("Bitiş saati", null=True, blank=True)
    gozlem_ziyareti_yapilmali = models.BooleanField(
        "Gözlem ziyareti yapılmalı mı?",
        default=False,
    )
    sozlesme_disi_islem_var = models.BooleanField(
        "Sözleşme dışı işlem var mı?",
        default=False,
    )
    # Makine ve Ekipmanlar (kullanılan ekipman bayrakları)
    skb = models.BooleanField("SKB", default=False)
    atomizor = models.BooleanField("Atomizör", default=False)
    pulverizator = models.BooleanField("Pülverizatör", default=False)
    termal_sis = models.BooleanField("Termal Sis.", default=False)
    ar_uz_ulv = models.BooleanField("Ar.Üz. ULV", default=False)
    elk_ulv = models.BooleanField("Elk. ULV", default=False)
    civi_tabancasi = models.BooleanField("Çivi Tabancası", default=False)
    oneriler = models.TextField("Öneriler", blank=True)
    not_alani = models.TextField("Not", blank=True)
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)
    # Bu iş kaydı hangi talebi kapatıyor (1-1). İş kaydı üzerinden seçilir; kaydedildiğinde talep durumu Yapıldı olur.
    kapatilan_talep = models.OneToOneField(
        "Talep",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kapatilan_is_kaydi",
        verbose_name="Kapatılan talep",
    )
    form_numarasi = models.CharField(
        "Form numarası",
        max_length=80,
        blank=True,
        editable=False,
        help_text="Otomatik: Müşteri kodu-Tesis kodu-YYYYMMDD (kapatılan talep varsa).",
    )

    class Meta:
        verbose_name = "İş kaydı"
        verbose_name_plural = "İş kayıtları"
        ordering = ["-tarih", "-created_at"]

    def save(self, *args, **kwargs):
        eski_talep_id = None
        if self.pk:
            try:
                eski = WorkRecord.objects.get(pk=self.pk)
                eski_talep_id = eski.kapatilan_talep_id
            except WorkRecord.DoesNotExist:
                pass
        self.form_numarasi = ""
        if self.kapatilan_talep_id:
            talep = getattr(self, "_kapatilan_talep_cache", None)
            if talep is None:
                talep = Talep.objects.select_related("customer", "facility").filter(pk=self.kapatilan_talep_id).first()
            if talep:
                self.form_numarasi = f"{talep.customer.kod}-{talep.facility.kod}-{self.tarih:%Y%m%d}"
        super().save(*args, **kwargs)
        if self.kapatilan_talep_id and self.kapatilan_talep.durum != "yapildi":
            self.kapatilan_talep.durum = "yapildi"
            self.kapatilan_talep.save(update_fields=["durum"])
        if eski_talep_id and eski_talep_id != self.kapatilan_talep_id:
            try:
                Talep.objects.get(pk=eski_talep_id).recalculate_durum()
            except Talep.DoesNotExist:
                pass

    def delete(self, *args, **kwargs):
        kapatilan_talep_id = self.kapatilan_talep_id
        super().delete(*args, **kwargs)
        if kapatilan_talep_id:
            try:
                Talep.objects.get(pk=kapatilan_talep_id).recalculate_durum()
            except Talep.DoesNotExist:
                pass

    def __str__(self):
        return f"{self.tarih} - {self.personel.get_username()}"


class WorkRecordFaaliyet(models.Model):
    """İş kaydında düzeltici/önleyici faaliyet: faaliyet seçimi + bayraklar (Kontrol, Kuruldu, ...)."""
    work_record = models.ForeignKey(
        WorkRecord,
        on_delete=models.CASCADE,
        related_name="faaliyetler",
        verbose_name="İş kaydı",
    )
    faaliyet_tanim = models.ForeignKey(
        FaaliyetTanim,
        on_delete=models.CASCADE,
        related_name="is_kaydi_satirlari",
        verbose_name="Faaliyet",
    )
    kontrol = models.BooleanField("Kontrol", default=False)
    kuruldu = models.BooleanField("Kuruldu", default=False)
    eklendi = models.BooleanField("Eklendi", default=False)
    sabitlendi = models.BooleanField("Sabitlendi", default=False)
    yeri_degistirildi = models.BooleanField("Yeri Değiştirildi", default=False)
    yenilendi = models.BooleanField("Yenilendi", default=False)

    class Meta:
        verbose_name = "İş kaydı faaliyet"
        verbose_name_plural = "İş kaydı faaliyetler"
        ordering = ["work_record", "faaliyet_tanim"]
        constraints = [
            models.UniqueConstraint(
                fields=["work_record", "faaliyet_tanim"],
                name="unique_workrecord_faaliyet",
            )
        ]

    def __str__(self):
        return f"{self.work_record} — {self.faaliyet_tanim}"


class WorkRecordIlac(models.Model):
    """İş kaydında kullanılan ilaç: İlaç Tanımlarından seçim + miktar."""
    work_record = models.ForeignKey(
        WorkRecord,
        on_delete=models.CASCADE,
        related_name="kullanilan_ilaclar",
        verbose_name="İş kaydı",
    )
    ilac_tanim = models.ForeignKey(
        IlacTanim,
        on_delete=models.CASCADE,
        related_name="is_kaydi_satirlari",
        verbose_name="İlaç",
    )
    miktar = models.DecimalField(
        "Miktar",
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    class Meta:
        verbose_name = "Kullanılan ilaç"
        verbose_name_plural = "Kullanılan ilaçlar"
        ordering = ["work_record", "ilac_tanim"]
        constraints = [
            models.UniqueConstraint(
                fields=["work_record", "ilac_tanim"],
                name="unique_workrecord_ilac",
            )
        ]

    def __str__(self):
        return f"{self.work_record} — {self.ilac_tanim}: {self.miktar}"


class WorkRecordUygulama(models.Model):
    """İş kaydında yapılan uygulama (tanım listesinden seçilen)."""
    work_record = models.ForeignKey(
        WorkRecord,
        on_delete=models.CASCADE,
        related_name="yapilan_uygulamalar",
        verbose_name="İş kaydı",
    )
    uygulama_tanim = models.ForeignKey(
        UygulamaTanim,
        on_delete=models.CASCADE,
        related_name="is_kaydi_satirlari",
        verbose_name="Uygulama",
    )

    class Meta:
        verbose_name = "Yapılan uygulama"
        verbose_name_plural = "Yapılan uygulamalar"
        constraints = [
            models.UniqueConstraint(
                fields=["work_record", "uygulama_tanim"],
                name="unique_workrecord_uygulama",
            )
        ]

    def __str__(self):
        return f"{self.work_record} — {self.uygulama_tanim}"


class TespitTanim(models.Model):
    """Tespit türlerinin tanım listesi (metin). İş kaydında tespitler buradan seçilir."""
    ad = models.CharField("Tespit", max_length=300)
    sira = models.PositiveSmallIntegerField("Sıra", default=0, help_text="Liste sıralaması")
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "Tespit tanımı"
        verbose_name_plural = "Tespit tanımları"
        ordering = ["sira", "ad"]

    def __str__(self):
        return self.ad


class WorkRecordTespit(models.Model):
    """İş kaydında yapılan tespit (tanım listesinden seçilen + yoğunluk + tespit eden)."""
    YOGUNLUK_AZ = "az"
    YOGUNLUK_COK = "cok"
    YOGUNLUK_ISTILA = "istila"
    YOGUNLUK_CHOICES = [
        (YOGUNLUK_AZ, "Az"),
        (YOGUNLUK_COK, "Çok"),
        (YOGUNLUK_ISTILA, "İstila"),
    ]
    TESPIT_EDEN_MUSTERI = "musteri"
    TESPIT_EDEN_FIRMA = "firma"
    TESPIT_EDEN_CHOICES = [
        (TESPIT_EDEN_MUSTERI, "Müşteri"),
        (TESPIT_EDEN_FIRMA, "Firma"),
    ]
    work_record = models.ForeignKey(
        WorkRecord,
        on_delete=models.CASCADE,
        related_name="tespitler",
        verbose_name="İş kaydı",
    )
    tespit_tanim = models.ForeignKey(
        TespitTanim,
        on_delete=models.CASCADE,
        related_name="is_kaydi_tespitleri",
        verbose_name="Tespit",
    )
    yogunluk = models.CharField(
        "Yoğunluk",
        max_length=20,
        choices=YOGUNLUK_CHOICES,
        default=YOGUNLUK_AZ,
    )
    tespit_eden = models.CharField(
        "Tespit eden",
        max_length=20,
        choices=TESPIT_EDEN_CHOICES,
        default=TESPIT_EDEN_FIRMA,
    )

    class Meta:
        verbose_name = "Tespit"
        verbose_name_plural = "Tespitler"
        ordering = ["work_record", "tespit_tanim"]

    def __str__(self):
        return f"{self.work_record} — {self.tespit_tanim} ({self.get_yogunluk_display()})"


class TalepTipi(models.Model):
    """Talep tipi: Şikayet, Yapılacak vb. Menüde sıraya göre listelenir."""
    ad = models.CharField("Ad", max_length=100)
    sira = models.PositiveSmallIntegerField("Sıra", default=0, help_text="Liste sıralaması")
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "Talep tipi"
        verbose_name_plural = "Talep tipleri"
        ordering = ["sira", "ad"]

    def __str__(self):
        return self.ad


class Talep(models.Model):
    """Talep. Tip TalepTipi ile seçilir; iş kaydı ile kapatılır."""
    DURUM_CHOICES = [
        ("beklemede", "Beklemede"),
        ("planlandi", "Planlandı"),
        ("yapildi", "Yapıldı"),
    ]
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="talepler",
        verbose_name="Müşteri",
    )
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="talepler",
        verbose_name="Tesis",
    )
    tarih = models.DateField("Talep tarihi")
    tip = models.ForeignKey(
        TalepTipi,
        on_delete=models.PROTECT,
        related_name="talepler",
        verbose_name="Tip",
    )
    aciklama = models.TextField("Açıklama")
    durum = models.CharField(
        "Durum",
        max_length=20,
        choices=DURUM_CHOICES,
        default="beklemede",
    )
    planlanan_tarih = models.DateField("Planlanan tarih", null=True, blank=True)
    planlanan_ekip = models.ForeignKey(
        "Ekip",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planlanan_talepler",
        verbose_name="Planlanan ekip",
    )
    # Kapatılan iş kaydı: İş kaydı formunda "Kapatılan talep" seçilince bu talep kapanır (reverse: talep.kapatilan_is_kaydi)
    iliski_talep = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bagli_talepler",
        verbose_name="İlişkili talep",
    )
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "Talep"
        verbose_name_plural = "Talepler"
        ordering = ["-tarih", "-created_at"]

    def save(self, *args, **kwargs):
        # Durum güncellemesi artık WorkRecord.save() içinde (iş kaydında "Kapatılan talep" seçildiğinde)
        # Planlanan tarih ve ekip doluysa durum = Planlandı (yapıldı değilse)
        if self.planlanan_tarih and self.planlanan_ekip_id and self.durum != "yapildi":
            self.durum = "planlandi"
        super().save(*args, **kwargs)

    def recalculate_durum(self):
        """İş kaydıyla kapatılmadığında durumu planlanan bilgilere göre günceller (Yapıldı dışı)."""
        if self.planlanan_tarih and self.planlanan_ekip_id:
            self.durum = "planlandi"
        else:
            self.durum = "beklemede"
        self.save(update_fields=["durum"])

    def __str__(self):
        return f"{self.tarih} {self.tip} - {self.customer.kod}"


class WorkRecordStationCount(models.Model):
    """İş kaydında istasyon bazlı sayım."""
    work_record = models.ForeignKey(
        WorkRecord,
        on_delete=models.CASCADE,
        related_name="station_counts",
        verbose_name="İş kaydı",
    )
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="sayim_kayitlari",
        verbose_name="İstasyon",
    )
    sayim_degeri = models.PositiveIntegerField(
        "Sayım değeri",
        default=0,
    )
    not_alani = models.CharField("Not", max_length=200, blank=True)
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "İş kaydı istasyon sayımı"
        verbose_name_plural = "İş kaydı istasyon sayımları"
        ordering = ["work_record", "station"]
        constraints = [
            models.UniqueConstraint(
                fields=["work_record", "station"],
                name="unique_workrecord_station",
            )
        ]

    def __str__(self):
        return f"{self.work_record} - {self.station.benzersiz_kod}: {self.sayim_degeri}"


class FaaliyetRaporu(models.Model):
    """İş kaydına bağlı faaliyet raporu. PDF oluşturulunca bu kayıtla saklanır."""
    work_record = models.OneToOneField(
        WorkRecord,
        on_delete=models.CASCADE,
        related_name="faaliyet_raporu",
        verbose_name="İş kaydı",
    )
    musteri_kod = models.CharField("Müşteri kodu", max_length=20)
    is_kaydi_kod = models.CharField("İş kaydı kodu (form no)", max_length=80)
    rapor_tarihi = models.DateField("Rapor tarihi")
    rapor_olusturuldu = models.BooleanField("Rapor oluşturuldu", default=False)
    pdf = models.FileField(
        "PDF",
        upload_to="faaliyet_raporlari/%Y/%m/",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "Faaliyet raporu"
        verbose_name_plural = "Faaliyet raporları"
        ordering = ["-rapor_tarihi", "-created_at"]

    def __str__(self):
        return f"{self.musteri_kod} / {self.is_kaydi_kod} ({self.rapor_tarihi})"
