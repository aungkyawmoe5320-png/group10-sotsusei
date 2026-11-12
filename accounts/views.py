from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import AccountEditForm, RoleLoginForm, SignUpForm
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
        messages.success(request, "アカウントを登録しました。ログインしてください。")
        return redirect("login")
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
