from django.shortcuts import render

from accounts.decorators import user_required

from .models import PreRegistration

@user_required
def preregister_list(request):
    entries = PreRegistration.objects.filter(user=request.user).prefetch_related("medications")
    return render(request, "preregister/list.html",{"entries":entries})