from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Facility(models.Model):
    """介護施設。介護士は必ずどこかの施設に所属する。"""

    facility_code = models.CharField("施設ID", max_length=20, unique=True)  # 例: F-0012
    name = models.CharField("施設名", max_length=100)

    class Meta:
        verbose_name = "施設"
        verbose_name_plural = "施設"

    def __str__(self):
        return f"{self.facility_code} {self.name}"


class UserManager(BaseUserManager):
    """メールアドレスでログインするためのユーザー作成処理。"""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("メールアドレスは必須です。")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # パスワードはハッシュ化して保存
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """システムの利用者。一般ユーザー（在宅介護の家族）または介護士。"""

    class Role(models.TextChoices):
        USER = "user", "一般ユーザー"
        CAREGIVER = "caregiver", "介護士"

    username = None  # ユーザー名は使わず、メールアドレスでログインする
    email = models.EmailField("メールアドレス", unique=True)
    name = models.CharField("氏名", max_length=50)
    role = models.CharField("利用の種類", max_length=20, choices=Role.choices, default=Role.USER)
    facility = models.ForeignKey(
        Facility,
        verbose_name="所属施設",
        on_delete=models.PROTECT,  # 介護士がいる施設は削除できない
        null=True,
        blank=True,
        related_name="caregivers",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"

    def __str__(self):
        return f"{self.name}（{self.get_role_display()}）"

    @property
    def is_caregiver(self):
        return self.role == self.Role.CAREGIVER
