from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import os

from .models import Assignment, Submission
from .forms import AssignmentForm, SubmissionForm, TeacherRemarkForm
from .utils import (
    extract_text_from_file,
    plagiarism_score,
    quality_score,
    generate_solution_with_ai,
    generate_feedback_with_ai,
)   

def teacher_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_teacher():
            messages.error(request, "Teacher access required.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def student_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_student():
            messages.error(request, "Student access required.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def assignment_list(request):
    if request.user.is_teacher():
        assignments = Assignment.objects.filter(teacher=request.user)
    else:
        assignments = Assignment.objects.all()
    return render(request, 'assignments/list.html', {'assignments': assignments})


@login_required
@teacher_required
def assignment_create(request):
    form = AssignmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        assignment = form.save(commit=False)
        assignment.teacher = request.user
        assignment.save()
        messages.success(request, f'Assignment "{assignment.title}" created successfully!')
        return redirect('assignment_detail', pk=assignment.pk)
    return render(request, 'assignments/create.html', {'form': form})


@login_required
def assignment_detail(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    user_submission = None
    if request.user.is_student():
        user_submission = Submission.objects.filter(
            assignment=assignment, student=request.user
        ).first()
    submissions = None
    if request.user.is_teacher() and assignment.teacher == request.user:
        submissions = assignment.submissions.select_related('student').all()
    return render(request, 'assignments/detail.html', {
        'assignment': assignment,
        'user_submission': user_submission,
        'submissions': submissions,
    })


@login_required
@student_required
def submit_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    existing = Submission.objects.filter(assignment=assignment, student=request.user).first()
    if existing:
        messages.warning(request, "You've already submitted this assignment.")
        return redirect('submission_detail', pk=existing.pk)

    form = SubmissionForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        submission = form.save(commit=False)
        submission.assignment = assignment
        submission.student = request.user

        # Extract text from uploaded file
        extracted = ''
        if submission.file:
            fs = FileSystemStorage(location=str(settings.MEDIA_ROOT))
            saved_name = fs.save(f'submissions/{submission.file.name}', submission.file)
            file_path = os.path.join(str(settings.MEDIA_ROOT), saved_name)
            extracted = extract_text_from_file(file_path)
            submission.extracted_text = extracted
            submission.file.name = saved_name

        # Text to analyze
        student_text = extracted or submission.text_content

        # Generate AI reference solution
        reference_text = ''
        try:
            reference_text = generate_solution_with_ai(assignment.description)
            submission.generated_solution = reference_text
        except Exception as e:
            print(f"AI solution generation failed: {e}")

        # Run plagiarism check
        if student_text and reference_text:
            plag_score, _ = plagiarism_score(student_text, reference_text)
            submission.plagiarism_score = plag_score

        # Quality score
        if student_text:
            submission.quality_score = quality_score(student_text)

        # AI feedback
        try:
            submission.ai_feedback = generate_feedback_with_ai(
                assignment.description,
                student_text,
                submission.plagiarism_score or 0,
                submission.quality_score or 0,
            )
        except Exception as e:
            print(f"AI feedback failed: {e}")

        # Auto-flag high plagiarism
        if submission.plagiarism_score and submission.plagiarism_score >= 70:
            submission.status = 'flagged'

        submission.save()
        messages.success(request, 'Assignment submitted and analyzed successfully!')
        return redirect('submission_detail', pk=submission.pk)

    return render(request, 'assignments/submit.html', {'assignment': assignment, 'form': form})


@login_required
def submission_detail(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    # Access control
    if request.user.is_student() and submission.student != request.user:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    if request.user.is_teacher() and submission.assignment.teacher != request.user:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    remark_form = None
    if request.user.is_teacher():
        remark_form = TeacherRemarkForm(request.POST or None, instance=submission)
        if request.method == 'POST' and remark_form.is_valid():
            from django.utils import timezone
            sub = remark_form.save(commit=False)
            sub.reviewed_at = timezone.now()
            sub.save()
            messages.success(request, 'Review saved.')
            return redirect('submission_detail', pk=pk)

    return render(request, 'assignments/submission_detail.html', {
        'submission': submission,
        'remark_form': remark_form,
    })


@login_required
def all_submissions(request):
    """Teacher view of all their students' submissions"""
    if not request.user.is_teacher():
        return redirect('dashboard')
    submissions = Submission.objects.filter(
        assignment__teacher=request.user
    ).select_related('student', 'assignment').order_by('-submitted_at')
    return render(request, 'assignments/all_submissions.html', {'submissions': submissions})
