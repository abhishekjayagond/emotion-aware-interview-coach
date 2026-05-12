"""
interview_questions.py
----------------------
Provides a rotating pool of realistic interview questions that are
displayed on-screen during the coaching session.

Questions are grouped by category so future expansion is easy.
"""

import random

# ── Question bank ─────────────────────────────────────────────────────────────
_QUESTIONS: list[tuple[str, str]] = [
    # (category, question)
    ("Behavioural",  "Tell me about yourself and your career journey so far."),
    ("Behavioural",  "Describe a time you handled a difficult team conflict."),
    ("Behavioural",  "Give an example of a project you led from start to finish."),
    ("Behavioural",  "Tell me about a mistake you made and what you learned."),
    ("Behavioural",  "Describe a situation where you had to meet a tight deadline."),
    ("Behavioural",  "How do you prioritise when you have multiple urgent tasks?"),
    ("Behavioural",  "Tell me about a time you received critical feedback."),
    ("Behavioural",  "Describe your biggest professional achievement to date."),
    ("Behavioural",  "How have you dealt with an underperforming colleague?"),
    ("Behavioural",  "Tell me about a risk you took and its outcome."),

    ("Technical",    "Explain the difference between a stack and a queue."),
    ("Technical",    "What is Big-O notation and why does it matter?"),
    ("Technical",    "Walk me through how you would debug a production issue."),
    ("Technical",    "How does garbage collection work in your primary language?"),
    ("Technical",    "Explain REST vs GraphQL — when would you use each?"),
    ("Technical",    "What design patterns have you applied in your projects?"),
    ("Technical",    "How do you approach writing unit tests for complex logic?"),
    ("Technical",    "Describe the differences between SQL and NoSQL databases."),
    ("Technical",    "What is the CAP theorem?"),
    ("Technical",    "How would you design a URL shortener like bit.ly?"),

    ("Situational",  "How would you handle receiving contradictory instructions?"),
    ("Situational",  "What would you do if a key team member quit mid-project?"),
    ("Situational",  "How would you respond if you disagreed with your manager?"),
    ("Situational",  "What steps would you take if you missed a deadline?"),
    ("Situational",  "How would you on-board yourself in a new team?"),
    ("Situational",  "You have two equally urgent tasks — how do you decide?"),
    ("Situational",  "A client is unhappy with your work — walk me through it."),
    ("Situational",  "How would you motivate a team that has lost momentum?"),
    ("Situational",  "What would you do if you spotted an ethical issue at work?"),
    ("Situational",  "How do you stay productive when working remotely?"),

    ("Career",       "Where do you see yourself in five years?"),
    ("Career",       "Why are you leaving your current role?"),
    ("Career",       "Why do you want to work at this company specifically?"),
    ("Career",       "What motivates you most in a work environment?"),
    ("Career",       "How do you keep your skills up to date?"),
    ("Career",       "What are your greatest strengths and weaknesses?"),
    ("Career",       "What kind of management style brings out your best work?"),
    ("Career",       "How do you define success in your role?"),
    ("Career",       "What would your previous manager say about you?"),
    ("Career",       "Do you have any questions for us?"),
]

# ── Public API ────────────────────────────────────────────────────────────────

def get_random_question() -> tuple[str, str]:
    """
    Return a random (category, question) tuple from the question bank.
    """
    return random.choice(_QUESTIONS)


def get_question_pool(n: int = 5) -> list[tuple[str, str]]:
    """
    Return *n* unique randomly selected questions.

    Args:
        n: Number of questions to return (clamped to pool size).

    Returns:
        List of (category, question) tuples.
    """
    return random.sample(_QUESTIONS, min(n, len(_QUESTIONS)))
