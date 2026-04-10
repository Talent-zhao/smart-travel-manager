import re

from django import forms

from .models import *

# 11 位大陆手机号：第二位 3–9，覆盖 13x–19x 等现行号段（含 187/188/192 等）
_CN_MOBILE_PATTERN = re.compile(r'^1[3-9]\d{9}$')


class Login(forms.Form):
    username = forms.CharField(
        label='用户名',
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control required'}),
    )
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control required'}),
    )


class Edit(forms.ModelForm):
    # 重写password字段，使其可选
    password = forms.CharField(
        label='登录密码',
        required=False,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'style': 'width:300px', 'placeholder': '留空则不修改密码'}),
    )
    
    class Meta:
        model = User
        fields = ['username', 'password', 'first_name', 'last_name', 'gender', 'age', 'phone', 'country', 'address', 'email', 'id_type', 'id_number', 'id_expiry_date']
        labels = {
            'username': '账号',
            'first_name': '姓氏',
            'last_name': '名字',
            'gender': '性别',
            'age': '年龄',
            'phone': '手机号码',
            'country': '国籍',
            'address': '地址',
            'email': '邮箱',
            'id_type': '证件类型',
            'id_number': '证件号',
            'id_expiry_date': '证件有效期',
        }
        widgets = {
            'username': forms.TextInput(
                attrs={'class': 'form-control', 'style': 'width:300px;', 'readonly': 'readonly'}),
            'first_name': forms.TextInput(
                attrs={'class': 'form-control', 'style': 'width:300px', 'placeholder': '请输入姓氏（同证件）'}),
            'last_name': forms.TextInput(
                attrs={'class': 'form-control', 'style': 'width:300px', 'placeholder': '请输入名字（同证件）'}),
            'gender': forms.RadioSelect(attrs={'class': 'my_radio'}),
            'age': forms.NumberInput(
                attrs={'class': 'form-control', 'style': 'width:300px', 'placeholder': '请输入年龄'}),
            'phone': forms.TextInput(
                attrs={'class': 'form-control', 'style': 'width:300px', 'placeholder': '请输入手机号码'}),
            'country': forms.Select(
                attrs={'class': 'form-control', 'style': 'width:300px'}),
            'address': forms.TextInput(
                attrs={'class': 'form-control', 'style': 'width:300px', 'placeholder': '请输入地址'}),
            'email': forms.EmailInput(
                attrs={'class': 'form-control', 'style': 'width:300px', 'placeholder': '请输入邮箱'}),
            'id_type': forms.Select(
                attrs={'class': 'form-control', 'style': 'width:300px'}),
            'id_number': forms.TextInput(
                attrs={'class': 'form-control', 'style': 'width:300px', 'placeholder': '请输入证件号'}),
            'id_expiry_date': forms.DateInput(
                attrs={'class': 'form-control', 'style': 'width:300px', 'type': 'date'}),
        }
    
    def clean_age(self):
        age = self.cleaned_data.get('age')
        if age and age <= 0:
            raise forms.ValidationError('年龄需要填大于0')
        return age
    
    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if phone:
            if not _CN_MOBILE_PATTERN.match(phone):
                raise forms.ValidationError('手机号码不合法！请输入11位中国大陆手机号。')
        return phone
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # 如果密码为空，保持原密码不变
        password = self.cleaned_data.get('password')
        if not password or password.strip() == '':
            # 从数据库重新获取原密码
            if user.pk:
                original_user = User.objects.get(pk=user.pk)
                user.password = original_user.password
        if commit:
            user.save()
        return user


class RegisterForm(forms.Form):
    username = forms.CharField(
        label='用户名',
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'style': 'margin-bottom:0'}),
    )
    password1 = forms.CharField(
        label='密码',
        max_length=128,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        label='确认密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    phone = forms.CharField(
        label='手机',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    gender = forms.ChoiceField(
        label='性别',
        widget=forms.RadioSelect(attrs={'class': 'my_radio'}),
        choices=GENDER
    )
    age = forms.IntegerField(label='年龄', help_text='请输入年龄')
    country = forms.ChoiceField(
        label='国籍',
        choices=COUNTRIES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='中国'
    )
    address = forms.CharField(
        label='地址',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')

        if len(username) < 1:
            raise forms.ValidationError(
                'Your username must be at least 6 characters long.'
            )
        elif len(username) > 50:
            raise forms.ValidationError('用户名太长啦')
        else:
            filter_result = User.objects.filter(username=username)
            if len(filter_result) > 0:
                raise forms.ValidationError('用户名已存在')
        return username

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if len(password1) < 6:
            raise forms.ValidationError('密码太短啦')
        # elif password1.isdigit():
        #     raise forms.ValidationError('密码不能是纯数字【需要是字母与数字组合】.')
        elif password1.isalpha():
            raise forms.ValidationError('密码不能是纯字母【需要是字母与数字组合】.')
        elif len(password1) > 20:
            raise forms.ValidationError('密码太长啦.')
        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('密码输入不匹配，请再输入一次')
        return password2

    def clean_age(self):
        age = self.cleaned_data.get('age')
        if age <= 0:
            raise forms.ValidationError('年龄需要填大于0')
        return age

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if phone and not _CN_MOBILE_PATTERN.match(phone):
            raise forms.ValidationError('手机号码不合法！请输入11位中国大陆手机号。')
        return phone
