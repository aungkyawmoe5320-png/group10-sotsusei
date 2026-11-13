import string

import re
import string
import unicodedata

from django import forms
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone

from .models import CareRecipient, User

PASSWORD_RULE_MESSAGE = "パスワードは16文字以上の英字、数字、記号を組み合わせてください。"


def is_strong_password(password):
    """16文字以上で、英字・数字・記号をすべて含むか。"""
    return (
        len(password) >= 16
        and any(c in string.ascii_letters for c in password)
        and any(c in string.digits for c in password)
        and any(c in string.punctuation for c in password)
    )

PHONE_RULE_MESSAGE = "電話番号は、数字とハイフンで入力してください（例: 090-1234-5678）。"


def normalize_phone(text):
    """全角の数字・ハイフンを半角にそろえ、前後の空白を取る。"""
    return unicodedata.normalize("NFKC", text).strip()


def is_valid_phone(phone):
    """数字とハイフンだけで、0から始まる10桁か11桁か。（例: 090-1234-5678、03-1234-5678）"""
    if not re.fullmatch(r"[0-9]+(-[0-9]+)*", phone):  # 先頭・末尾・連続のハイフンはだめ
        return False
    digits = phone.replace("-", "")
    if not digits.startswith("0") or len(digits) not in (10, 11):
        return False
    if digits[:3] in ("070", "080", "090"):  # 携帯電話は11桁
        return len(digits) == 11
    return True
class BootstrapMixin:
    """全ての入力欄に Bootstrap の見た目（form-control）を付ける。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs.setdefault("class", "form-control")


class SignUpForm(BootstrapMixin, forms.ModelForm):
    """アカウント登録（Create）。1人目の要介護者もあわせて登録する。"""

    name = forms.CharField(label="介護者氏名", max_length=50)
    recipient_name = forms.CharField(
        label="要介護者氏名",
        max_length=50,
        widget=forms.TextInput(attrs={"placeholder": "例: 山田 花子"}),
    )
    password = forms.CharField(label="パスワード", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["name", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています。")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not is_strong_password(password):
            raise forms.ValidationError(PASSWORD_RULE_MESSAGE)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            with transaction.atomic():  # アカウントと要介護者は、両方できるか、両方できないか
                user.save()
                CareRecipient.objects.create(user=user, name=self.cleaned_data["recipient_name"])
        return user


class AccountEditForm(BootstrapMixin, forms.ModelForm):
    """アカウント情報の編集（Update）。電話番号は、ここからだけ入力できる。"""

    phone = forms.CharField(
        label="電話番号",
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={"type": "tel", "placeholder": "例: 090-1234-5678", "autocomplete": "tel"}),
    )

    class Meta:
        model = User
        fields = ["name", "email", "phone"]
        labels = {"name": "介護者氏名"}

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています。")
        return email

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if phone and not is_valid_phone(phone):
            raise forms.ValidationError(PHONE_RULE_MESSAGE)
        return phone  # 空のままなら「未登録」として保存される

class CareRecipientForm(BootstrapMixin, forms.ModelForm):
    """要介護者の追加・設定。"""

    age = forms.IntegerField(
        label="年齢",
        required=False,
        min_value=0,
        max_value=130,
        error_messages={
            "invalid": "年齢は0〜130の数字で入力してください。",
            "min_value": "年齢は0〜130の数字で入力してください。",
            "max_value": "年齢は0〜130の数字で入力してください。",
        },
    )
    birthday = forms.DateField(
        label="誕生日",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        error_messages={"invalid": "誕生日を正しく入力してください。"},
    )
    relation = forms.ChoiceField(
        label="介護者との関係",
        required=False,
        choices=[("", "選択しない")] + [(r, r) for r in CareRecipient.RELATIONS],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = CareRecipient
        fields = ["name", "age", "birthday", "relation"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["name"].widget.attrs.update(
            {"class": "form-control form-control-lg", "placeholder": "例: 山田 次郎"}
        )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        same_name = self.user.recipients.filter(name=name).exclude(pk=self.instance.pk)
        if same_name.exists():
            raise forms.ValidationError("同じ氏名の要介護者がすでに登録されています。")
        return name

    def clean_birthday(self):
        birthday = self.cleaned_data.get("birthday")
        if birthday:
            today = timezone.localdate()
            age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
            if birthday > today or age > 130:
                raise forms.ValidationError("誕生日を正しく入力してください。")
        return birthday

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("birthday"):
            cleaned["age"] = None  # 誕生日があれば、年齢は誕生日から自動で計算する
        return cleaned

    def save(self, commit=True):
        recipient = super().save(commit=False)
        recipient.user = self.user
        if commit:
            recipient.save()
        return recipient

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["name"].widget.attrs.update(
            {"class": "form-control form-control-lg", "placeholder": "例: 山田 次郎"}
        )
        if self.instance.pk:  # 設定画面では、誕生日があれば計算した年齢を入れておく
            self.initial["age"] = self.instance.display_age


class LoginForm(BootstrapMixin, forms.Form):
    """ログイン（メールアドレスとパスワード）。"""

    email = forms.EmailField(
        label="メールアドレス",
        widget=forms.EmailInput(attrs={"placeholder": "example@city.jp"}),
    )
    password = forms.CharField(label="パスワード", widget=forms.PasswordInput)

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        cleaned = super().clean()
        email, password = cleaned.get("email"), cleaned.get("password")
        if not email or not password:
            return cleaned
        user = authenticate(self.request, email=email.lower(), password=password)
        if user is None:
            # どちらが違うのかは教えない（存在するメールを推測させないため）
            raise forms.ValidationError("メールアドレスまたはパスワードが正しくありません。")
        self.user = user
        return cleaned