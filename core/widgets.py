"""Admin'de kare (1:1) kırpma için görsel yükleme widget'ı."""

from django.forms import ClearableFileInput


class ImageCropInput(ClearableFileInput):
    """Görsel seçildiğinde kare kırpma modalı açar. Kullanıcı hizalayıp kırpar, kırpılmış kare kaydedilir."""

    def __init__(self, attrs=None, *args, **kwargs):
        default_attrs = {"accept": "image/*", "class": "image-crop-input"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs, *args, **kwargs)
