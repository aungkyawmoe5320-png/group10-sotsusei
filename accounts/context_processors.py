from .current import get_current_recipient


def current_recipient(request):
    """全ての画面で {{ current_recipient }} を使えるようにする（ヘッダーに名前を出すため）。"""
    if not request.user.is_authenticated:
        return {}
    return {"current_recipient": get_current_recipient(request)}