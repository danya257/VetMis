# forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import re

class CustomUserCreationForm(UserCreationForm):
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput,
        help_text="Минимум 8 символов. Не используйте только цифры или слишком распространённые пароли."
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput,
        help_text="Введите тот же самый пароль ещё раз."
    )

    class Meta:
        model = User
        fields = ("username",)

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        # Минимальная длина
        if len(password) < 8:
            raise ValidationError("Пароль слишком короткий. Минимум 8 символов.", code='password_too_short')
        # Только цифры
        if password.isdigit():
            raise ValidationError("Введённый пароль состоит только из цифр.", code='password_only_numbers')
        # Широко распространённые пароли
        common_passwords = ['12345678','qwerty','password','пароль','123456789','11111111','87654321','1234567']
        for p in common_passwords:
            if password == p:
                raise ValidationError("Введённый пароль слишком широко распространён.", code='password_too_common')
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Пароли не совпадают.")
        return cleaned_data
class CustomAuthenticationForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, label="Запомнить меня")