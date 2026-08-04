"""
Seed script for EasyEarn's starter tasks (surveys, videos, reviews,
ebooks, ads).

HOW TO RUN:
    python manage.py shell < scripts/seed_tasks.py

Or paste the whole file's contents directly into `python manage.py shell`.

This is SAFE TO RE-RUN — it checks for an existing Task with the same
title before creating a new one (get_or_create), so running it twice
won't create duplicates.

PLACEHOLDERS TO REPLACE: every `external_url` below is a placeholder —
swap in the real video/ad/ebook links you want users to open before
this goes live. I didn't invent fake-but-real-looking URLs; these are
obviously-placeholder example.com links so nothing here could be
mistaken for a working link if you forget to update it.
"""

from tasks.models import Task, SurveyQuestion

# --- Surveys ---------------------------------------------------------------
# Each survey Task can have multiple questions; a user earns Ksh 30 per
# question they answer correctly (see SURVEY_PAYOUT_PER_CORRECT_ANSWER_KES
# in apps/tasks/models.py).

survey_task, _ = Task.objects.get_or_create(
    task_type=Task.TaskType.SURVEY,
    title="General Knowledge Quick Survey",
    defaults={
        "description": "Answer a few quick questions to earn.",
        "is_active": True,
    },
)

survey_questions = [
    {
        "question_text": "What is the capital of Kenya?",
        "correct_answer": "Nairobi",
        "options": "Nairobi,Mombasa,Kisumu,Nakuru",
    },
    {
        "question_text": "2 + 2 = ?",
        "correct_answer": "4",
        "options": "3,4,5,6",
    },
    {
        "question_text": "Which currency is used in Kenya?",
        "correct_answer": "KES",
        "options": "KES,UGX,TZS,NGN",
    },
]

for q in survey_questions:
    SurveyQuestion.objects.get_or_create(
        task=survey_task,
        question_text=q["question_text"],
        defaults={
            "correct_answer": q["correct_answer"],
            "options": q["options"],
        },
    )

# --- Videos ------------------------------------------------------------
# Each pays a flat Ksh 129.33 (FIXED_TASK_PAYOUT_KES) on submission.

video_tasks = [
    {
        "title": "Watch: Intro to EasyEarn",
        "description": "Watch a short intro video about how EasyEarn works.",
        "external_url": "https://example.com/videos/intro-to-easyearn",  # REPLACE with real video URL
    },
    {
        "title": "Watch: Product Highlight Reel",
        "description": "Watch a short product highlight clip.",
        "external_url": "https://example.com/videos/product-highlight",  # REPLACE with real video URL
    },
]

for v in video_tasks:
    Task.objects.get_or_create(
        task_type=Task.TaskType.VIDEO,
        title=v["title"],
        defaults={
            "description": v["description"],
            "external_url": v["external_url"],
            "is_active": True,
        },
    )

# --- Reviews -------------------------------------------------------------

review_tasks = [
    {
        "title": "Review: Rate a Popular Mobile App",
        "description": "Write a short review of a mobile app after trying it out.",
        "external_url": "https://example.com/apps/sample-app",  # REPLACE with real app URL
    },
]

for r in review_tasks:
    Task.objects.get_or_create(
        task_type=Task.TaskType.REVIEW,
        title=r["title"],
        defaults={
            "description": r["description"],
            "external_url": r["external_url"],
            "is_active": True,
        },
    )

# --- Ebooks ----------------------------------------------------------------

ebook_tasks = [
    {
        "title": "Read: Getting Started Guide",
        "description": "Read a short ebook guide.",
        "external_url": "https://example.com/ebooks/getting-started",  # REPLACE with real ebook URL
    },
]

for e in ebook_tasks:
    Task.objects.get_or_create(
        task_type=Task.TaskType.EBOOK,
        title=e["title"],
        defaults={
            "description": e["description"],
            "external_url": e["external_url"],
            "is_active": True,
        },
    )

# --- Ads ---------------------------------------------------------------

ad_tasks = [
    {
        "title": "Click: Sponsor Ad #1",
        "description": "Click through a sponsor ad.",
        "external_url": "https://example.com/ads/sponsor-1",  # REPLACE with real ad URL
    },
    {
        "title": "Click: Sponsor Ad #2",
        "description": "Click through a sponsor ad.",
        "external_url": "https://example.com/ads/sponsor-2",  # REPLACE with real ad URL
    },
]

for a in ad_tasks:
    Task.objects.get_or_create(
        task_type=Task.TaskType.AD,
        title=a["title"],
        defaults={
            "description": a["description"],
            "external_url": a["external_url"],
            "is_active": True,
        },
    )

print(f"Done. Total tasks in database: {Task.objects.count()}")
print(f"Survey questions on '{survey_task.title}': {survey_task.survey_questions.count()}")