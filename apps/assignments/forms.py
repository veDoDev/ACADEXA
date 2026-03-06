from django import forms
from .models import Assignment, Submission


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'subject', 'deadline', 'max_marks']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Assignment title'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 5, 'placeholder': 'Describe the assignment...'}),
            'subject': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Computer Science'}),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'max_marks': forms.NumberInput(attrs={'class': 'form-input'}),
        }


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['file', 'text_content']
        widgets = {
            'text_content': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 8,
                'placeholder': 'Or paste your answer here...'
            }),
            'file': forms.FileInput(attrs={'class': 'form-input', 'accept': '.pdf,.docx,.txt'}),
        }

    def clean(self):
        cleaned = super().clean()
        file = cleaned.get('file')
        text = cleaned.get('text_content')
        if not file and not text:
            raise forms.ValidationError("Please either upload a file or enter your answer as text.")
        return cleaned


class TeacherRemarkForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['teacher_remarks', 'marks_awarded', 'status']
        widgets = {
            'teacher_remarks': forms.Textarea(attrs={'class': 'form-input', 'rows': 4}),
            'marks_awarded': forms.NumberInput(attrs={'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-input'}),
        }
