from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.assignments.models import Assignment
from apps.communications.models import Channel


class Command(BaseCommand):
    help = "Seed demo users, channels, and assignments. Safe to run multiple times."

    def handle(self, *args, **options):
        User = get_user_model()

        teachers = [
            {
                "username": "prof_sharma",
                "password": "demo1234",
                "first_name": "Prof",
                "last_name": "Sharma",
                "role": "teacher",
                "department": "CSE",
            },
            {
                "username": "prof_los",
                "password": "demo12345",
                "first_name": "Prof",
                "last_name": "Los",
                "role": "teacher",
                "department": "CSE",
            },
        ]

        students = [
            {
                "username": "student_1yr",
                "password": "demo1234",
                "first_name": "Student",
                "last_name": "One",
                "role": "student",
                "department": "1st year",
            },
            {
                "username": "student_2yr",
                "password": "demo1234",
                "first_name": "Student",
                "last_name": "Two",
                "role": "student",
                "department": "2nd year",
            },
        ]

        created_users = {}

        for u in teachers + students:
            user, created = User.objects.get_or_create(
                username=u["username"],
                defaults={
                    "first_name": u["first_name"],
                    "last_name": u["last_name"],
                    "role": u["role"],
                    "department": u["department"],
                    "email": f"{u['username']}@demo.local",
                },
            )
            if created:
                user.set_password(u["password"])
                user.save(update_fields=["password"])
            else:
                # keep existing password
                pass
            created_users[u["username"]] = user

        prof_los = created_users["prof_los"]
        prof_sharma = created_users["prof_sharma"]

        # Channels for Prof Los (Teams-like)
        channel_specs = [
            ("General", "General announcements and discussion"),
            ("1st year", "Cohort channel for 1st year"),
            ("2nd year", "Cohort channel for 2nd year"),
            ("DBMS", "DBMS subject channel"),
            ("AOA", "Analysis of Algorithms subject channel"),
        ]

        for name, desc in channel_specs:
            ch, _ = Channel.objects.get_or_create(
                owner=prof_los,
                name=name,
                defaults={"description": desc},
            )
            # owner always a member
            ch.members.add(prof_los)

            # add students based on channel name
            if name == "1st year":
                ch.members.add(created_users["student_1yr"])
            elif name == "2nd year":
                ch.members.add(created_users["student_2yr"])
            elif name in {"General", "DBMS", "AOA"}:
                ch.members.add(created_users["student_1yr"], created_users["student_2yr"])

        now = timezone.now()

        # Demo assignments
        demo_assignments = [
            (
                prof_sharma,
                "DBMS: ER Diagram Basics",
                "Create an ER diagram for a simple Library Management System. Explain entities, relationships, and constraints.",
                "DBMS",
                now + timedelta(days=3),
                100,
            ),
            (
                prof_sharma,
                "DBMS: Normalization Practice",
                "Given a sample table with anomalies, normalize it to 3NF and justify each step.",
                "DBMS",
                now + timedelta(days=7),
                100,
            ),
            (
                prof_los,
                "AOA: Time Complexity Drill",
                "Analyze the time complexity of given pseudo-code snippets and derive Big-O.",
                "AOA",
                now + timedelta(days=4),
                100,
            ),
            (
                prof_los,
                "AOA: Divide & Conquer",
                "Explain divide and conquer paradigm and solve one classic problem with recurrence relation.",
                "AOA",
                now + timedelta(days=8),
                100,
            ),
        ]

        for teacher, title, desc, subject, deadline, max_marks in demo_assignments:
            Assignment.objects.get_or_create(
                teacher=teacher,
                title=title,
                defaults={
                    "description": desc,
                    "subject": subject,
                    "deadline": deadline,
                    "max_marks": max_marks,
                },
            )

        self.stdout.write(self.style.SUCCESS("Seed complete: demo users, channels, and assignments ready."))
