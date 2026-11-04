"""アンケートの定義と、入力チェック。

質問・選択肢は SURVEY_SECTIONS だけで決まる（画面はこの定義から作る）。
  type: radio（1つ選ぶ） / checkbox（当てはまるものすべて） / text（1行） / textarea（短い文章）
  exclusive: checkbox で、ほかの選択肢と同時に選べない選択肢（「なし」「不明」など）
  detail: 選択肢のほかに入力する内容（when があれば、その選択肢を選んだとき必須）
  required（セクション）: そのセクションの質問は、すべて必須
"""

_NONE_YES_UNKNOWN = [("none", "なし"), ("yes", "あり"), ("unknown", "不明")]

SURVEY_SECTIONS = [
    {"key": "life", "mark": "①", "title": "命に関わる情報", "required": True, "questions": [
        {"key": "allergy", "label": "アレルギー", "type": "checkbox", "exclusive": ["none", "unknown"],
         "options": [("none", "なし"), ("food", "食べ物"), ("drug", "薬"), ("other", "その他"), ("unknown", "不明")],
         "detail": {"key": "allergy_other", "label": "内容", "when": "other", "maxlen": 50}},
        {"key": "insulin", "label": "インスリン注射", "type": "radio", "options": _NONE_YES_UNKNOWN},
        {"key": "implants", "label": "体内の人工物", "type": "checkbox", "exclusive": ["none", "unknown"],
         "options": [("none", "なし"), ("pacemaker", "ペースメーカー"), ("joint", "人工関節"), ("shunt", "シャント"), ("other", "その他"), ("unknown", "不明")]},
        {"key": "treatments", "label": "医療処置", "type": "checkbox", "exclusive": ["none", "unknown"],
         "options": [("none", "なし"), ("catheter", "尿道バルーン"), ("stoma", "ストーマ"), ("oxygen", "酸素"), ("other", "その他"), ("unknown", "不明")]},
    ]},
    {"key": "meal", "mark": "②", "title": "食事", "questions": [
        {"key": "diet_form", "label": "食形態", "type": "radio",
         "options": [("normal", "普通"), ("minced", "刻み"), ("pureed", "ミキサー"), ("unknown", "不明")]},
        {"key": "thickener", "label": "とろみ", "type": "radio", "options": _NONE_YES_UNKNOWN},
        {"key": "choking", "label": "むせ", "type": "radio",
         "options": [("none", "なし"), ("sometimes", "ときどき"), ("often", "よくある"), ("unknown", "不明")]},
    ]},
    {"key": "toilet_bath", "mark": "③", "title": "排泄・入浴", "questions": [
        {"key": "toileting", "label": "排泄", "type": "radio",
         "options": [("toilet", "トイレ"), ("portable", "ポータブル"), ("pad", "オムツ・パッド"), ("unknown", "不明")]},
        {"key": "bathing", "label": "入浴", "type": "radio",
         "options": [("home", "自宅で入っている"), ("no", "入っていない"), ("unknown", "不明")],
         "detail": {"key": "bathing_help", "label": "介助の有無", "maxlen": 50}},
    ]},
    {"key": "move", "mark": "④", "title": "移動", "questions": [
        {"key": "walking", "label": "歩行", "type": "radio",
         "options": [("independent", "自立"), ("cane", "杖・歩行器"), ("wheelchair", "車椅子"), ("unknown", "不明")]},
        {"key": "fall", "label": "転倒（1年以内）", "type": "radio", "options": _NONE_YES_UNKNOWN},
    ]},
    {"key": "home", "mark": "⑤", "title": "認知・コミュニケーション・自宅での様子", "questions": [
        {"key": "dementia", "label": "認知症", "type": "radio", "options": _NONE_YES_UNKNOWN},
        {"key": "senses", "label": "聞こえ・見え", "type": "checkbox", "exclusive": ["none"],
         "options": [("hearing_aid", "補聴器"), ("glasses", "眼鏡"), ("none", "どちらも使用なし")]},
        {"key": "nickname", "label": "呼ばれ方", "type": "text", "maxlen": 30},
        {"key": "home_behaviors", "label": "自宅で見られること（当てはまるものすべて）", "type": "checkbox", "exclusive": ["none", "unknown"],
         "options": [("none", "特にない"), ("angry", "怒りっぽい・大声を出す"), ("violent", "手や足が出る"),
                     ("refuse", "介助を強く拒否する（入浴・排泄・服薬など）"), ("restless", "落ち着かない・同じことを繰り返す"),
                     ("night", "夜に不安定になる"), ("unknown", "不明")]},
        {"key": "home_notes", "label": "きっかけ・嫌がること・普段と違うサイン・落ち着く対応（短記入）", "type": "textarea", "maxlen": 200,
         "hint": "例：「急かされると怒る」「トイレ誘導で嫌がる」「食欲が落ちたら体調不良のサイン」「好きな歌で落ち着く」"},
    ]},
    {"key": "person", "mark": "⑥", "title": "本人らしさ", "questions": [
        {"key": "background", "label": "出身地・主な仕事・趣味（1行）", "type": "text", "maxlen": 100},
    ]},
]

SURVEY_CONSENT_LABEL = "ご本人らしい対応をするために、記載内容を施設内で共有することに同意します。"
SURVEY_SIGNATURE_MAXLEN = 30

# 個人情報の使用範囲の選択肢（アンケートの①〜⑥の区分から作る）
SURVEY_USE_SCOPES = [(sec["key"], f"{sec['mark']} {sec['title']}") for sec in SURVEY_SECTIONS]
# 全セクションの質問を1つのリストにしたもの
SURVEY_QUESTIONS = [q for sec in SURVEY_SECTIONS for q in sec["questions"]]


def empty_survey():
    """何も答えていないアンケート（画面を開いた最初の状態）。"""
    answers = {}
    for q in SURVEY_QUESTIONS:
        answers[q["key"]] = [] if q["type"] == "checkbox" else ""
        if "detail" in q:
            answers[q["detail"]["key"]] = ""
    answers.update(use_scope=[], consent=False, signature="")
    return answers


def read_survey(post):
    """送られたフォーム（request.POST）から、アンケートの答えを取り出す。"""
    answers = {}
    for q in SURVEY_QUESTIONS:
        key, options = q["key"], [v for v, _ in q.get("options", [])]
        if q["type"] == "checkbox":
            chosen = set(post.getlist(key))
            answers[key] = [v for v in options if v in chosen]  # 選択肢の順に並べる。知らない値は無視
        elif q["type"] == "radio":
            answers[key] = post.get(key, "") if post.get(key, "") in options else ""
        else:
            answers[key] = post.get(key, "").strip()
        detail = q.get("detail")
        if detail:
            text = post.get(detail["key"], "").strip()
            # 「その他」を選んでいないときの内容は、消す
            answers[detail["key"]] = text if not detail.get("when") or detail["when"] in answers[key] else ""
    chosen_scope = set(post.getlist("use_scope"))
    answers["use_scope"] = [key for key, _ in SURVEY_USE_SCOPES if key in chosen_scope]
    answers["consent"] = "consent" in post
    answers["signature"] = post.get("signature", "").strip()
    return answers


def survey_errors(answers):
    """アンケートの入力の誤り（メッセージのリスト。なければ空）。"""
    errors = []
    for sec in SURVEY_SECTIONS:
        for q in sec["questions"]:
            value, label = answers[q["key"]], q["label"]
            names = dict(q.get("options", []))
            if sec.get("required") and not value:
                errors.append(f"「{label}」を選んでください。")
            if q["type"] == "checkbox":
                exclusive = [v for v in value if v in q.get("exclusive", [])]
                if exclusive and len(value) > 1:
                    errors.append(f"「{label}」の「{names[exclusive[0]]}」は、ほかの項目と同時に選べません。")
            elif q["type"] in ("text", "textarea") and len(value) > q["maxlen"]:
                errors.append(f"「{label}」は{q['maxlen']}文字以内で入力してください。")
            detail = q.get("detail")
            if detail:
                text = answers[detail["key"]]
                if detail.get("when") and detail["when"] in value and not text:
                    errors.append(f"「{label}」の「{names[detail['when']]}」の{detail['label']}を入力してください。")
                if len(text) > detail["maxlen"]:
                    errors.append(f"「{label}」の{detail['label']}は{detail['maxlen']}文字以内で入力してください。")
    if not answers["consent"]:
        errors.append("同意にチェックを入れてください。")
    else:
        if not answers["use_scope"]:
            errors.append("「個人情報の使用範囲」を1つ以上選んでください。")
        if not answers["signature"]:
            errors.append("同意する場合は、署名を入力してください。")
    if len(answers["signature"]) > SURVEY_SIGNATURE_MAXLEN:
        errors.append(f"署名は{SURVEY_SIGNATURE_MAXLEN}文字以内で入力してください。")
    return errors