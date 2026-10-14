from django.shortcuts import redirect, render

from accounts.decorators import user_required

from .models import PreRegistration


def _own_entry(request, pk):
    """Return the logged-in user's own pre-registration, or None."""
    return PreRegistration.objects.filter(pk=pk, user=request.user).prefetch_related("medications").first()


@user_required
def preregister_list(request):
    entries = PreRegistration.objects.filter(user=request.user).prefetch_related("medications")
    return render(request, "preregister/list.html", {"entries": entries})


@user_required
def preregister_detail(request, pk):
    entry = _own_entry(request, pk)
    if entry is None:
        return redirect("preregister")
    return render(request, "preregister/detail.html", {"e": entry})