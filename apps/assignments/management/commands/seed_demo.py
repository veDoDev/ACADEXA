"""
Management command to seed demo data for Acadexa.
Run: python manage.py seed_demo
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Seeds demo data: 1 teacher, 3 students, 2 assignments, 4 submissions'

    def handle(self, *args, **kwargs):
        from apps.accounts.models import User
        from apps.assignments.models import Assignment, Submission
        from apps.communications.models import Message

        self.stdout.write('🌱 Seeding demo data...')

        # Create teacher
        teacher, _ = User.objects.get_or_create(
            username='prof_sharma',
            defaults={
                'first_name': 'Dr. Ravi',
                'last_name': 'Sharma',
                'email': 'ravi.sharma@acadexa.edu',
                'role': 'teacher',
                'department': 'Computer Science',
            }
        )
        teacher.set_password('demo1234')
        teacher.save()
        self.stdout.write(f'  ✓ Teacher: {teacher.username} / demo1234')

        # Create students
        students = []
        student_data = [
            ('arjun_k', 'Arjun', 'Kumar', 'arjun@student.acadexa.edu'),
            ('priya_m', 'Priya', 'Mehta', 'priya@student.acadexa.edu'),
            ('rohan_s', 'Rohan', 'Singh', 'rohan@student.acadexa.edu'),
        ]
        for username, first, last, email in student_data:
            s, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'email': email,
                    'role': 'student',
                    'department': 'Computer Science',
                }
            )
            s.set_password('demo1234')
            s.save()
            students.append(s)
            self.stdout.write(f'  ✓ Student: {s.username} / demo1234')

        # Create assignments
        a1, _ = Assignment.objects.get_or_create(
            title='Introduction to Machine Learning',
            defaults={
                'teacher': teacher,
                'description': (
                    'Explain the concept of supervised vs unsupervised learning. '
                    'Provide real-world examples of each. Discuss the key differences, '
                    'common algorithms used in each paradigm, and their applications in industry. '
                    'Your answer should be at least 500 words and include relevant technical details.'
                ),
                'subject': 'Artificial Intelligence',
                'deadline': timezone.now() + timedelta(days=7),
                'max_marks': 100,
            }
        )
        a2, _ = Assignment.objects.get_or_create(
            title='Data Structures and Complexity Analysis',
            defaults={
                'teacher': teacher,
                'description': (
                    'Compare and contrast arrays and linked lists in terms of time and space complexity. '
                    'When would you use one over the other? Provide implementation examples in Python '
                    'and analyze Big O complexity for common operations like insertion, deletion, and search.'
                ),
                'subject': 'Data Structures',
                'deadline': timezone.now() + timedelta(days=5),
                'max_marks': 50,
            }
        )
        self.stdout.write(f'  ✓ 2 assignments created')

        # Create submissions with varied plagiarism scores
        submission_data = [
            (students[0], a1, 22.5, 74.3, 'submitted',
             'Supervised learning uses labeled data where the algorithm learns from input-output pairs. '
             'For example, email spam detection trains on emails marked as spam or not spam. '
             'Unsupervised learning works with unlabeled data to discover hidden patterns. '
             'Clustering customer segments in marketing is a classic unsupervised application. '
             'Key supervised algorithms include Linear Regression, Decision Trees, and Neural Networks. '
             'Common unsupervised algorithms are K-Means clustering and Principal Component Analysis.'),
            (students[1], a1, 78.4, 45.1, 'flagged',
             'Supervised learning is a type of machine learning where the model is trained on labeled data. '
             'The algorithm learns from training examples that include both the input data and the correct output. '
             'Unsupervised learning involves finding patterns in data without labeled responses. '
             'The machine learning model must discover the underlying structure or distribution in the data.'),
            (students[2], a1, 15.8, 81.2, 'reviewed',
             'Machine learning paradigms fundamentally differ in their approach to data. '
             'In supervised learning, we provide the algorithm with annotated examples — imagine teaching '
             'a child by showing them pictures with labels. Unsupervised learning is more like letting '
             'the child explore and discover patterns independently. Real applications of supervised learning '
             'include medical diagnosis, fraud detection, and image recognition systems. '
             'Unsupervised learning powers recommendation engines, anomaly detection, and customer segmentation.'),
            (students[0], a2, 41.2, 62.0, 'submitted',
             'Arrays store elements in contiguous memory locations providing O(1) random access. '
             'Linked lists store elements with pointers to the next node, providing O(n) access. '
             'Arrays are better when you need frequent random access to elements. '
             'Linked lists excel at frequent insertions and deletions at the beginning.'),
        ]

        for student, assignment, plag, quality, status, text in submission_data:
            sub, created = Submission.objects.get_or_create(
                assignment=assignment,
                student=student,
                defaults={
                    'text_content': text,
                    'extracted_text': text,
                    'plagiarism_score': plag,
                    'quality_score': quality,
                    'status': status,
                    'ai_feedback': (
                        f'This submission demonstrates {"good" if quality > 65 else "adequate"} understanding of the topic. '
                        f'The plagiarism score of {plag}% is {"concerning and requires attention" if plag > 60 else "within acceptable range"}. '
                        f'Consider {"providing more original analysis" if plag > 40 else "expanding on the technical details"} '
                        f'to improve the quality of your response.'
                    ),
                }
            )
            if status == 'flagged':
                sub.status = 'flagged'
                sub.save()

        self.stdout.write(f'  ✓ 4 submissions with scores seeded')

        # Seed a message
        Message.objects.get_or_create(
            sender=students[0],
            receiver=teacher,
            defaults={
                'subject': 'Question about Assignment 1',
                'body': 'Dear Professor Sharma,\n\nI had a question about the ML assignment. '
                        'Should we include code examples in our explanation of supervised learning algorithms?\n\n'
                        'Thank you,\nArjun',
                'is_read': False,
            }
        )
        self.stdout.write(f'  ✓ Demo message seeded')

        self.stdout.write(self.style.SUCCESS('\n✅ Demo data seeded successfully!'))
        self.stdout.write('\n📋 Login credentials:')
        self.stdout.write('  Teacher:  prof_sharma / demo1234')
        self.stdout.write('  Student:  arjun_k / demo1234')
        self.stdout.write('  Student:  priya_m / demo1234')
        self.stdout.write('  Student:  rohan_s / demo1234')
