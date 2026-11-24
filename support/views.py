from urllib.parse import urlencode

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from accounts.decorators import recipient_required, user_required

from .content import (
    CARE_STEPS_EXAMPLE,
    CARE_TOPICS,
    POSTURES,
    SUPPORT_EXAMPLE,
    SUPPORT_SCENES,
)

MSG_NEED_CHOICE = "体の向きと内容のイラストを選んでください。"


def _find(items, key):
    """key が一致するものを返す。なければ None。"""
    return next((item for item in items if item["key"] == key), None)


@require_http_methods(["GET", "HEAD"])
@user_required
@recipient_required
def support(request):  # お困りサポートのトップ（介護手順 / 緊急対応）
    return render(request, "support/top.html")


@require_http_methods(["GET", "HEAD"])
@user_required
@recipient_required
def support_emergency(request):  # 緊急対応① 場面のイラストを選ぶ
    return render(request, "support/emergency_list.html", {"scenes": SUPPORT_SCENES})


@require_http_methods(["GET", "HEAD"])
@user_required
@recipient_required
def support_emergency_detail(request, key):  # 緊急対応② 選んだ場面の解決法を表示
    scene = _find(SUPPORT_SCENES, key)
    if scene is None:  # 知らない場面なら、一覧に戻す
        return redirect("support_emergency")
    return render(request, "support/emergency_detail.html", {
        "scene": scene,
        "sol": scene.get("solution", SUPPORT_EXAMPLE),
    })


@require_http_methods(["GET", "POST"])
@user_required
@recipient_required
def care_steps(request):  # 介護手順① 「1.体の向き」→「2.内容」のイラストを順に選ぶ
    # POST のときは、送られた選択を優先する（「内容を選び直す」で来たときの URL のクエリ値では上書きしない）
    source = request.POST if request.method == "POST" else request.GET
    posture = _find(POSTURES, source.get("posture", ""))
    topic = _find(CARE_TOPICS, source.get("topic", ""))
    if request.method == "POST":
        if posture and topic:
            query = urlencode({"posture": posture["key"], "topic": topic["key"]})
            return redirect(f"{reverse('care_steps_result')}?{query}")
        messages.error(request, MSG_NEED_CHOICE)
    return render(request, "support/care_steps.html", {
        "postures": POSTURES,
        "topics": CARE_TOPICS,
        "posture": posture,  # 選ばれていなければ None（そのときは「1.体の向き」から）
        "topic": topic,
    })


@require_http_methods(["GET", "HEAD"])
@user_required
@recipient_required
def care_steps_result(request):  # 介護手順② 選んだ内容の手順を表示
    posture = _find(POSTURES, request.GET.get("posture", ""))
    topic = _find(CARE_TOPICS, request.GET.get("topic", ""))
    if posture is None or topic is None:  # どちらかが不正なら、選び直しへ
        return redirect("care_steps")
    back_query = urlencode({"posture": posture["key"], "topic": topic["key"]})
    return render(request, "support/care_steps_result.html", {
        "posture": posture,
        "topic": topic,
        "sol": CARE_STEPS_EXAMPLE,
        "back_url": f"{reverse('care_steps')}?{back_query}",
    })
