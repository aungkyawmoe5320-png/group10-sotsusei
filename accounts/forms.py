import string

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
    """アカウント情報の編集（Update）。"""

    class Meta:
        model = User
        fields = ["name", "email"]
        labels = {"name": "介護者氏名"}

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています。")
        return email


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


class RoleLoginForm(BootstrapMixin, forms.Form):
    """ログイン。（介護士用の処理は、のちほど整理して取り除く）"""

    email = forms.EmailField(
        label="メールアドレス",
        widget=forms.EmailInput(attrs={"placeholder": "example@city.jp"}),
    )
    facility_code = forms.CharField(label="施設ID", max_length=20, required=False)
    password = forms.CharField(label="パスワード", widget=forms.PasswordInput)

    def __init__(self, *args, role, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role
        self.request = request
        self.user = None
        if role == User.Role.CAREGIVER:
            self.fields["facility_code"].required = True

    def clean(self):
        cleaned = super().clean()
        email, password = cleaned.get("email"), cleaned.get("password")
        if not email or not password:
            return cleaned
        user = authenticate(self.request, email=email.lower(), password=password)
        # どの理由で失敗しても同じ文言にする（存在するメールを推測させないため）
        error = "メールアドレス・施設ID・パスワードのいずれかが正しくありません。"
        if user is None or user.role != self.role:
            raise forms.ValidationError(error)
        if self.role == User.Role.CAREGIVER:
            code = (cleaned.get("facility_code") or "").strip()
            if user.facility is None or user.facility.facility_code != code:
                raise forms.ValidationError(error)
        self.user = user
        return cleaned