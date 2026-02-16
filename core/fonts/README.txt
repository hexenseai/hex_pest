PDF çıktılarında Türkçe karakter (ş, ğ, ü, ö, ç, ı, İ vb.) desteği için:

1) Windows: Otomatik olarak sistem Arial fontu kullanılır.

2) Ubuntu/Linux sunucu:
   - Önerilen: fonts-dejavu-core paketini yükleyin:
     sudo apt install fonts-dejavu-core
   - Uygulama otomatik olarak /usr/share/fonts/truetype/dejavu/ altındaki
     DejaVu fontlarını kullanacaktır.

3) Alternatif (proje içi fontlar): Bu klasöre aşağıdaki dosyaları koyun:
    DejaVuSans.ttf
    DejaVuSans-Bold.ttf
   İndirme: https://dejavu-fonts.github.io/ (Downloads → TTF)

Font bulunamazsa PDF oluşturulur ancak Türkçe karakterler boş/kutu görünebilir.
