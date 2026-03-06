from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, LoginForm
from .models import User
from apps.assignments.models import Assignment, Submission
from apps.communications.models import Message


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Welcome to Acadexa, {user.first_name}!')
        return redirect('dashboard')
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect('dashboard')
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard_view(request):
    user = request.user
    context = {'user': user}

    if user.is_teacher():
        assignments = Assignment.objects.filter(teacher=user).order_by('-created_at')
        submissions = Submission.objects.filter(assignment__teacher=user).order_by('-submitted_at')
        total_submissions = submissions.count()
        pending_review = submissions.filter(status='submitted').count()
        flagged = submissions.filter(plagiarism_score__gte=60).count()
        avg_plagiarism = 0
        if total_submissions:
            scores = [s.plagiarism_score for s in submissions if s.plagiarism_score is not None]
            avg_plagiarism = round(sum(scores) / len(scores), 1) if scores else 0

        recent_submissions = submissions[:5]
        context.update({
            'assignments': assignments,
            'recent_submissions': recent_submissions,
            'total_submissions': total_submissions,
            'pending_review': pending_review,
            'flagged': flagged,
            'avg_plagiarism': avg_plagiarism,
            'total_assignments': assignments.count(),
        })
        return render(request, 'accounts/teacher_dashboard.html', context)

    else:
        submissions = Submission.objects.filter(student=user).order_by('-submitted_at')
        available = Assignment.objects.exclude(
            id__in=submissions.values_list('assignment_id', flat=True)
        ).order_by('-created_at')
        messages_count = Message.objects.filter(receiver=user, is_read=False).count()
        context.update({
            'submissions': submissions,
            'available_assignments': available,
            'unread_messages': messages_count,
            'total_submitted': submissions.count(),
        })
        return render(request, 'accounts/student_dashboard.html', context)
