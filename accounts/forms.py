from django import forms
from django.contrib.auth import authenticate, password_validation

from .models import Facility, User


class BootstrapMixin:
    """全ての入力欄に Bootstrap の見た目（form-control）を付ける。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs.setdefault("class", "form-control")


class SignUpForm(BootstrapMixin, forms.ModelForm):
    """アカウント登録（Create）。介護士は施設IDが必須。"""

    facility_code = forms.CharField(label="施設ID（介護士のみ）", max_length=20, required=False)
    password = forms.CharField(label="パスワード", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["role", "name", "email"]
        widgets = {"role": forms.RadioSelect}

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています。")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") == User.Role.CAREGIVER:
            code = (cleaned.get("facility_code") or "").strip()
            if not code:
                self.add_error("facility_code", "介護士は施設IDを入力してください。")
            else:
                try:
                    cleaned["facility"] = Facility.objects.get(facility_code=code)
                except Facility.DoesNotExist:
                    self.add_error("facility_code", "この施設IDは登録されていません。")
        password = cleaned.get("password")
        if password:
            # Djangoの基準（8文字以上、数字だけ不可など）でチェック
            temp_user = User(email=cleaned.get("email", ""), name=cleaned.get("name", ""))
            try:
                password_validation.validate_password(password, temp_user)
            except forms.ValidationError as e:
                self.add_error("password", e)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.facility = self.cleaned_data.get("facility") if user.is_caregiver else None
        if commit:
            user.save()
        return user


class AccountEditForm(BootstrapMixin, forms.ModelForm):
    """アカウント情報の編集（Update）。"""

    class Meta:
        model = User
        fields = ["name", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています。")
        return email


class RoleLoginForm(BootstrapMixin, forms.Form):
    """ログイン。一般ユーザーと介護士で同じフォーム、介護士は施設IDも確認する。"""

    email = forms.EmailField(label="メールアドレス")
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
