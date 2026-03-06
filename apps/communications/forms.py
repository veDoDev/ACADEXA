from django import forms
from .models import Message
from apps.accounts.models import User


class MessageForm(forms.ModelForm):
    receiver = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={'class': 'form-input'})
    )

    class Meta:
        model = Message
        fields = ['receiver', 'subject', 'body']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Subject'}),
            'body': forms.Textarea(attrs={'class': 'form-input', 'rows': 6, 'placeholder': 'Write your message...'}),
        }

    def __init__(self, *args, user=None, initial_receiver=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Students message teachers; teachers message students
            if user.role == 'student':
                self.fields['receiver'].queryset = User.objects.filter(role='teacher')
            else:
                self.fields['receiver'].queryset = User.objects.filter(role='student')
        if initial_receiver:
            self.fields['receiver'].initial = initial_receiver
