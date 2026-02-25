"""Müşteri portalı için context processor'lar."""


def user_profile(request):
    """Oturum açmış kullanıcının profilini context'e ekler."""
    profile = None
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
    return {"user_profile": profile}
