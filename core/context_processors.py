"""Müşteri portalı için context processor'lar."""


def user_profile(request):
    """Oturum açmış kullanıcının profilini ve admin geçiş linki bilgisini context'e ekler."""
    profile = None
    show_admin_link = False
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        show_admin_link = getattr(request.user, "is_staff", False)
    return {"user_profile": profile, "show_admin_link": show_admin_link}
