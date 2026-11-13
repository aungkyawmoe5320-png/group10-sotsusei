from .survey_def import SURVEY_SECTIONS


def _answer_text(q, answers):
    """1つの質問の答えを、画面に出す文字にする。"""
    value = answers.get(q["key"])
    names = dict(q.get("options", []))
    if q["type"] == "checkbox":
        text = "、".join(names[v] for v in (value or []) if v in names)
    elif q["type"] == "radio":
        text = names.get(value, "")
    else:
        text = value or ""
    detail = q.get("detail")
    if detail and answers.get(detail["key"]):
        extra = answers[detail["key"]]
        text = f"{text}（{extra}）" if text else extra
    return text


def build_sections(recipient, pdf):
    """PDFに載せる内容を、見出しごとのリストにして返す（recipient: 要介護者）。
    まとめる項目で選んだものと、アンケートの「個人情報の使用範囲」で許可された区分だけを載せる。
    """
    items, answers = pdf.items, pdf.survey
    sections = []

    if items.get("basic"):
        age = recipient.display_age
        sections.append({"heading": "基本情報", "text": "", "details": [
            f"氏名: {recipient.name}",
            f"年齢: {age}歳" if age is not None else "年齢: 未登録",
            f"介護者との関係: {recipient.relation or '未登録'}",
        ]})

    ids = items.get("prereg", [])
    if ids:
        details = []
        for e in recipient.pre_registrations.filter(id__in=ids).prefetch_related("medications"):
            parts = [f"【{e.condition}】"]
            if e.diagnosis:
                parts.append(f"病名: {e.diagnosis}")
            if e.hospital:
                parts.append(f"病院: {e.hospital}")
            if e.care_level:
                parts.append(f"要介護度: {e.care_level}")
            meds = "、".join(f"{m.name}（{m.timing}）" for m in e.medications.all())
            if meds:
                parts.append(f"薬: {meds}")
            parts.append(f"注意事項: {e.notes}")
            details.append("　".join(parts))
        if details:
            sections.append({"heading": "事前登録", "text": "", "details": details})

    if items.get("schedule"):
        details = [f"{s.time:%H:%M} {s.title}" for s in recipient.schedules.all()]
        sections.append({"heading": "スケジュール", "text": "" if details else "登録された予定はありません。", "details": details})

    # アンケート: 同意した使用範囲の区分だけを載せる
    allowed = set(answers.get("use_scope", []))
    for sec in SURVEY_SECTIONS:
        if sec["key"] not in allowed:
            continue
        details = []
        for q in sec["questions"]:
            text = _answer_text(q, answers)
            if text:
                details.append(f"{q['label']}: {text}")
        if details:
            sections.append({"heading": f"{sec['mark']} {sec['title']}", "text": "", "details": details})

    return sections