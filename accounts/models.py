from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


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
    """システムの利用者（在宅介護の家族）。メールアドレスでログインする。"""

    username = None  # ユーザー名は使わず、メールアドレスでログインする
    email = models.EmailField("メールアドレス", unique=True)
    name = models.CharField("氏名", max_length=50)
    phone = models.CharField("電話番号", max_length=20, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"

    def __str__(self):
        return self.name


class CareRecipient(models.Model):
    """要介護者（介護される人）。1つのアカウントに、複数人を登録できる。"""

    RELATIONS = ["母", "父", "義母", "義父", "祖母", "祖父", "配偶者", "子", "きょうだい", "その他"]

    user = models.ForeignKey(
        User,
        verbose_name="介護者",
        on_delete=models.CASCADE,  # アカウントを削除したら、要介護者も一緒に削除する
        related_name="recipients",
    )
    name = models.CharField("要介護者氏名", max_length=50)
    age = models.PositiveSmallIntegerField("年齢", null=True, blank=True)
    birthday = models.DateField("誕生日", null=True, blank=True)
    relation = models.CharField(
        "介護者との関係", max_length=10, blank=True, choices=[(r, r) for r in RELATIONS]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "要介護者"
        verbose_name_plural = "要介護者"
        ordering = ["id"]

    def __str__(self):
        return self.name

    @property
    def display_age(self):
        """誕生日があれば誕生日から計算する。なければ、入力された年齢（未入力なら None）。"""
        if self.birthday:
            today = timezone.localdate()
            had_birthday = (today.month, today.day) >= (self.birthday.month, self.birthday.day)
            return today.year - self.birthday.year - (0 if had_birthday else 1)
        return self.age