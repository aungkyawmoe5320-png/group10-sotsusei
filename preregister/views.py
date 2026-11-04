from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import user_required

from .forms import PreRegistrationForm
from .models import CareLevel, PreRegistration, Timing

MSG_ADDED = "事前登録を追加しました。"
MSG_UPDATED = "事前登録を更新しました。"
MSG_DELETED = "事前登録を削除しました。"


def _own_entry(request, pk):
    """Return the logged-in user's own pre-registration, or None."""
    return PreRegistration.objects.filter(pk=pk, user=request.user).prefetch_related("medications").first()


def _form_page(request, form, mode, cancel_url):
    for error in form.error_list():
        messages.error(request, error)
    return render(request, "preregister/form.html", {
        "form": form,
        "mode": mode,
        "cancel_url": cancel_url,
        "care_level_choices": [("", "選択しない"), *CareLevel.choices],
        "timing_choices": Timing.choices,
    })


@user_required
def preregister_list(request):
    entries = PreRegistration.objects.filter(user=request.user).prefetch_related("medications")
    return render(request, "preregister/list.html", {"entries": entries})


@user_required
def preregister_new(request):
    if request.method == "POST":
        form = PreRegistrationForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, MSG_ADDED)
            return redirect("preregister")
    else:
        form = PreRegistrationForm(user=request.user)
    return _form_page(request, form, "new", cancel_url=reverse("preregister"))


@user_required
def preregister_detail(request, pk):
    entry = _own_entry(request, pk)
    if entry is None:
        return redirect("preregister")
    return render(request, "preregister/detail.html", {"e": entry})


@user_required
def preregister_edit(request, pk):
    entry = _own_entry(request, pk)
    if entry is None:
        return redirect("preregister")
    if request.method == "POST":
        form = PreRegistrationForm(request.POST, instance=entry, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, MSG_UPDATED)
            return redirect("preregister_detail", pk=entry.pk)
    else:
        form = PreRegistrationForm(instance=entry, user=request.user)
    return _form_page(request, form, "edit", cancel_url=reverse("preregister_detail", args=[entry.pk]))


@user_required
@require_POST
def preregister_delete(request, pk):
    entry = _own_entry(request, pk)
    if entry is not None:
        entry.delete()
        messages.info(request, MSG_DELETED)
    return redirect("preregister")