from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import user_required

from .content import build_sections
from .models import SummaryPdf
from .survey_def import (
    SURVEY_CONSENT_LABEL,
    SURVEY_SECTIONS,
    SURVEY_USE_SCOPES,
    empty_survey,
    read_survey,
    survey_errors,
)

PENDING_KEY = "summary_pending"  # 項目を選んだあと、アンケートに答え終わるまで、選んだ項目をおぼえておく（セッション）

MSG_NEED_ITEM = "まとめる項目を1つ以上選んでください。"
MSG_NEED_SELECT = "先に、まとめる項目を選んでください。"
MSG_CREATED = "PDFを作成しました。"
MSG_UPDATED = "PDFを更新しました。"
MSG_DELETED = "PDFを削除しました。"
MSG_DOWNLOAD = "PDFのダウンロードは準備中です（今回は表示のみです）。"


def _own_pdf(request):
    """ログイン中の本人のPDF。なければ None。"""
    return SummaryPdf.objects.filter(user=request.user).first()


def _default_items(user):
    """まとめる項目の初期値（すべて選ぶ）。"""
    return {"basic": True, "prereg": list(user.pre_registrations.values_list("id", flat=True)), "schedule": True}


def _items_empty(items):
    return not (items["basic"] or items["prereg"] or items["schedule"])


def _select_page(request, items):
    """「まとめる項目を選ぶ」画面。items は、選択の状態。"""
    user = request.user
    return render(request, "summary/summary.html", {
        "form": items,
        "pdf": _own_pdf(request),
        "prereg": user.pre_registrations.prefetch_related("medications"),
        "schedule_count": user.schedules.count(),
    })


@user_required
def summary(request):  # ① まとめる項目の選択
    pdf = _own_pdf(request)
    # アンケートから戻ったときは選んだ項目のまま。2回目からは前回の選択。初めてはすべて選択
    items = request.session.get(PENDING_KEY) or (pdf.items if pdf else _default_items(request.user))
    return _select_page(request, items)


@require_POST
@user_required
def summary_save(request):  # ② 項目を決めて、アンケートへ
    post = request.POST
    chosen = {int(v) for v in post.getlist("prereg") if v.isdigit()}
    own_ids = set(request.user.pre_registrations.values_list("id", flat=True))
    items = {
        "basic": "basic" in post,
        "prereg": sorted(chosen & own_ids),  # 自分の事前登録だけを受け付ける
        "schedule": "schedule" in post,
    }
    if _items_empty(items):
        messages.error(request, MSG_NEED_ITEM)
        return _select_page(request, items)  # 選んだ状態のまま、選び直してもらう
    request.session[PENDING_KEY] = items
    return redirect("summary_survey")


@user_required
def summary_survey(request):  # ③ アンケート。答えたあとに、PDFを作成・更新する
    items = request.session.get(PENDING_KEY)
    if items is None:  # 項目を選ばずに開いたとき
        messages.warning(request, MSG_NEED_SELECT)
        return redirect("summary")
    answers = empty_survey()  # 最初は、何も入力・選択されていない状態
    if request.method == "POST":
        answers = read_survey(request.POST)
        errors = survey_errors(answers)
        if errors:
            for message in errors:
                messages.error(request, message)
        else:
            _, created = SummaryPdf.objects.update_or_create(
                user=request.user, defaults={"items": items, "survey": answers}
            )
            request.session.pop(PENDING_KEY, None)
            messages.success(request, MSG_CREATED if created else MSG_UPDATED)
            return redirect("summary_detail")
    return render(request, "summary/survey.html", {
        "form": answers,
        "sections": SURVEY_SECTIONS,
        "consent_label": SURVEY_CONSENT_LABEL,
        "use_scopes": SURVEY_USE_SCOPES,
        "pdf": _own_pdf(request),
    })


@user_required
def summary_detail(request):  # ④ 作成したPDFを見る
    pdf = _own_pdf(request)
    if pdf is None:
        return redirect("summary")
    return render(request, "summary/detail.html", {"pdf": pdf, "sections": build_sections(request.user, pdf)})


@require_POST
@user_required
def summary_delete(request):  # ⑥ PDFを削除する（確認ダイアログのあとに送る）
    pdf = _own_pdf(request)
    if pdf is not None:
        pdf.delete()  # アンケートの答えも一緒に消える
        messages.success(request, MSG_DELETED)
    return redirect("summary")


@user_required
def summary_download(request):  # ⑤ ダウンロード（今回は準備中の知らせだけ）
    if _own_pdf(request) is None:
        return redirect("summary")
    messages.info(request, MSG_DOWNLOAD)
    return redirect("summary_detail")