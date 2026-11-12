from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AccountEditForm, CareRecipientForm, RoleLoginForm, SignUpForm
from .models import User


def index(request):
    """トップ画面。ログイン済みならホームへ、未ログインならログイン画面へ。"""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


def login_view(request):
    """ログイン画面（一般ユーザー用の1つだけ）。"""
    form = RoleLoginForm(request.POST or None, role="user", request=request)
    if request.method == "POST" and form.is_valid():
        login(request, form.user)
        return redirect("dashboard")
    return render(request, "accounts/login.html", {"form": form})


@require_POST
def logout_view(request):
    """ログアウト（安全のため POST のみ受け付ける）。"""
    logout(request)
    messages.info(request, "ログアウトしました。")
    return redirect("login")


@login_required
def dashboard(request):
    """ログイン後のホーム。役割ごとに画面を分ける（中身は来週以降に実装）。"""
    if request.user.is_caregiver:
        return render(request, "accounts/dashboard_caregiver.html")
    return render(request, "accounts/dashboard_user.html")


# ---- アカウント CRUD ----
def account_new(request):  # Create
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)  # 登録したら、そのままログインする
        messages.success(request, "アカウントを登録しました。")
        return redirect("dashboard")
    return render(request, "accounts/account_form.html", {"form": form, "mode": "new"})


@login_required
def account_detail(request):  # Read
    return render(request, "accounts/account_detail.html")


@login_required
def account_edit(request):  # Update
    form = AccountEditForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "アカウント情報を更新しました。")
        return redirect("account_detail")
    return render(request, "accounts/account_form.html", {"form": form, "mode": "edit"})


@login_required
def account_delete(request):  # Delete
    if request.method == "POST":
        user = request.user
        logout(request)
        user.delete()
        messages.info(request, "アカウントを削除しました。")
        return redirect("login")
    return render(request, "accounts/account_delete.html")


# ---- 要介護者 ----
@login_required
def care_recipient_new(request):  # 要介護者の追加
    form = CareRecipientForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        recipient = form.save()
        messages.success(request, f"{recipient.name}さんを要介護者に追加しました。")
        return redirect("account_detail")
    return render(request, "accounts/care_recipient_form.html", {"form": form, "mode": "new"})


@login_required
def care_recipient_edit(request, pk):  # 要介護者の設定
    recipient = get_object_or_404(request.user.recipients, pk=pk)  # 他の人の要介護者は 404
    form = CareRecipientForm(request.POST or None, instance=recipient, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "要介護者の設定を更新しました。")
        return redirect("account_detail")
    context = {
        "form": form,
        "mode": "edit",
        "recipient": recipient,
        "can_delete": request.user.recipients.count() > 1,
    }
    return render(request, "accounts/care_recipient_form.html", context)


@login_required
@require_POST
def care_recipient_delete(request, pk):  # 要介護者の削除（1人だけのときは削除できない）
    recipient = get_object_or_404(request.user.recipients, pk=pk)
    if request.user.recipients.count() <= 1:
        messages.warning(request, "要介護者が1人だけのときは、削除できません。")
        return redirect("care_recipient_edit", pk=pk)
    name = recipient.name
    recipient.delete()
    messages.info(request, f"{name}さんを要介護者から削除しました。")
    return redirect("account_detail")