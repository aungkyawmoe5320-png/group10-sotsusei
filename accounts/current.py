SESSION_KEY = "care_recipient_id"


def get_current_recipient(request):
    """選択中の要介護者を返す。まだ選ばれていなければ None（1人だけなら、自動で選ぶ）。"""
    user = request.user
    if not user.is_authenticated:
        return None
    recipients = list(user.recipients.all())
    selected_id = request.session.get(SESSION_KEY)
    current = next((r for r in recipients if r.pk == selected_id), None)
    if current is None and len(recipients) == 1:
        current = recipients[0]
        request.session[SESSION_KEY] = current.pk
    return current