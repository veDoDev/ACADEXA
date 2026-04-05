from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, LoginForm
from .models import User
from apps.assignments.models import Assignment, Submission
from apps.communications.models import Message
from django.http import HttpResponse
import csv
import json


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

@login_required
def profile_edit(request):
    from .forms import ProfileUpdateForm
    form = ProfileUpdateForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('dashboard')
    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
def teacher_classes_view(request):
    if not request.user.is_teacher():
        return redirect('dashboard')
        
    submissions = Submission.objects.filter(assignment__teacher=request.user).select_related('student')
    
    classes_data = {}
    for sub in submissions:
        student = sub.student
        dept = student.department or "Unassigned"
        
        if dept not in classes_data:
            classes_data[dept] = {}
            
        if student.pk not in classes_data[dept]:
            classes_data[dept][student.pk] = {
                'student': student,
                'total_assignments': 0,
                'flagged': 0,
                'plag_scores': [],
            }
            
        student_data = classes_data[dept][student.pk]
        student_data['total_assignments'] += 1
        if sub.status == 'flagged':
            student_data['flagged'] += 1
        if sub.plagiarism_score is not None:
            student_data['plag_scores'].append(sub.plagiarism_score)
            
    context_classes = []
    for dept, students_dict in classes_data.items():
        student_list = []
        for s_pk, s_data in students_dict.items():
            avg_plag = sum(s_data['plag_scores']) / len(s_data['plag_scores']) if s_data['plag_scores'] else 0
            s_data['avg_plagiarism'] = round(avg_plag, 1)
            student_list.append(s_data)
        context_classes.append({
            'department': dept,
            'students': sorted(student_list, key=lambda x: x['student'].get_full_name()),
            'student_count': len(student_list)
        })
        
    context_classes.sort(key=lambda x: x['department'])
    return render(request, 'accounts/classes.html', {'classes': context_classes})


@login_required
def analytics_dashboard(request):
    if not request.user.is_teacher():
        return redirect('dashboard')

    submissions = Submission.objects.filter(
        assignment__teacher=request.user
    ).select_related('student', 'assignment').order_by('student__username', 'submitted_at')

    per_student = {}
    for sub in submissions:
        s = sub.student
        key = s.pk
        if key not in per_student:
            per_student[key] = {
                'student': s,
                'submissions': [],
                'plag_scores': [],
                'quality_scores': [],
            }
        per_student[key]['submissions'].append(sub)
        if sub.plagiarism_score is not None:
            per_student[key]['plag_scores'].append(float(sub.plagiarism_score))
        if sub.quality_score is not None:
            per_student[key]['quality_scores'].append(float(sub.quality_score))

    students = []
    for data in per_student.values():
        ps = data['plag_scores']
        qs = data['quality_scores']
        data['avg_plagiarism'] = round(sum(ps) / len(ps), 1) if ps else 0
        data['avg_quality'] = round(sum(qs) / len(qs), 1) if qs else 0
        data['total_submissions'] = len(data['submissions'])
        students.append(data)

    students.sort(key=lambda x: x['student'].get_full_name() or x['student'].username)

    chart_payload = {
        'labels': [
            (s['student'].get_full_name() or s['student'].username)
            for s in students
        ],
        'plag': [s['avg_plagiarism'] for s in students],
        'quality': [s['avg_quality'] for s in students],
    }

    return render(request, 'accounts/analytics.html', {
        'students': students,
        'chart_payload': chart_payload,
    })


@login_required
def export_submissions_csv(request):
    if not request.user.is_teacher():
        return redirect('dashboard')

    qs = Submission.objects.filter(
        assignment__teacher=request.user
    ).select_related('student', 'assignment').order_by('-submitted_at')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="submissions_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'submitted_at',
        'assignment_title',
        'subject',
        'student_username',
        'student_name',
        'status',
        'plagiarism_score',
        'confidence_score',
        'quality_score',
        'marks_awarded',
    ])

    for sub in qs:
        writer.writerow([
            sub.submitted_at.isoformat() if sub.submitted_at else '',
            sub.assignment.title,
            sub.assignment.subject,
            sub.student.username,
            sub.student.get_full_name() or '',
            sub.status,
            sub.plagiarism_score if sub.plagiarism_score is not None else '',
            sub.confidence_score if sub.confidence_score is not None else '',
            sub.quality_score if sub.quality_score is not None else '',
            sub.marks_awarded if sub.marks_awarded is not None else '',
        ])

    return response
