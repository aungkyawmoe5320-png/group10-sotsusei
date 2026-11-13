from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .current import get_current_recipient


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


def recipient_required(view):
    """選択中の要介護者が必要な画面に付ける（user_required の内側に重ねて使う）。
    選ばれていれば request.recipient に入れる。選ばれていなければ、選ぶ画面へ送る。"""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        recipient = get_current_recipient(request)
        if recipient is None:
            if request.user.recipients.exists():  # 2人以上いて、まだ選んでいない
                return redirect("care_recipient_select")
            messages.warning(request, "先に要介護者を追加してください。")
            return redirect("account_detail")
        request.recipient = recipient
        return view(request, *args, **kwargs)

    return wrapper