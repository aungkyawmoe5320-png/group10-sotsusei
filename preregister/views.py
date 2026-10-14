from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.decorators import user_required

from .forms import PreRegistrationForm
from .models import CareLevel, PreRegistration, Timing

MSG_ADDED = "事前登録を追加しました。"


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