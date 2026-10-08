from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def caregiver_required(view):
    """介護士だけが開ける画面に付ける。未ログインはトップへ、一般ユーザーはホームへ。"""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "ログインしてください。")
            return redirect("index")
        if not request.user.is_caregiver:
            messages.warning(request, "この画面は介護士のみ利用できます。")
            return redirect("dashboard")
        return view(request, *args, **kwargs)

    return wrapper


def user_required(view):
    """一般ユーザーだけが開ける画面に付ける（来週以降の事前登録・体調履歴などで使う）。"""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "ログインしてください。")
            return redirect("index")
        if request.user.is_caregiver:
            messages.warning(request, "この画面は一般ユーザーのみ利用できます。")
            return redirect("dashboard")
        return view(request, *args, **kwargs)

    return wrapper
