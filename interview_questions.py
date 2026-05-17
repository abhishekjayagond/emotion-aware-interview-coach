"""
interview_questions.py
----------------------
Handles interview progression and dynamic question generation.
Adapts to the user's detected emotional state to simulate a real interviewer.
"""

import random

STAGES = ["Intro", "Technical", "Behavioral", "Situational", "Wrap-up"]

_QUESTIONS = {
    "Intro": {
        "calm": [
            "Tell me about yourself and your career journey.",
            "Walk me through your resume."
        ],
        "nervous": [
            "Welcome! Let's start easy. What's a project you really enjoyed working on?",
            "Thanks for taking the time today. How has your week been so far?"
        ]
    },
    "Technical": {
        "calm": [
            "Explain REST vs GraphQL. When would you use each?",
            "How do you approach writing unit tests for complex logic?",
            "What design patterns have you applied in your recent projects?"
        ],
        "nervous": [
            "What's a programming language or tool you feel most comfortable with?",
            "Can you explain a technical concept you recently learned?",
            "Walk me through how you usually debug an issue."
        ]
    },
    "Behavioral": {
        "calm": [
            "Describe a time you handled a difficult team conflict.",
            "Tell me about a risk you took and its outcome.",
            "How do you prioritize when you have multiple urgent tasks?"
        ],
        "nervous": [
            "Tell me about a time when a team project went really well.",
            "What's an accomplishment you're most proud of?",
            "How do you usually like to organize your daily work?"
        ]
    },
    "Situational": {
        "calm": [
            "What would you do if a key team member quit mid-project?",
            "How would you handle receiving contradictory instructions from two managers?",
            "A client is unhappy with your work — walk me through how you handle it."
        ],
        "nervous": [
            "If you were stuck on a problem, how would you go about finding help?",
            "Imagine you're joining a new team. What's your first step to onboard?",
            "How do you stay productive and focused when working remotely?"
        ]
    },
    "Wrap-up": {
        "calm": [
            "Where do you see yourself in five years?",
            "Do you have any questions for us about the role or company?"
        ],
        "nervous": [
            "You did great today! Do you have any questions for us?",
            "Thanks for your time. Is there anything else you'd like to share?"
        ]
    }
}

def get_question_for_stage(stage: str, emotion: str) -> tuple[str, str]:
    """
    Returns a (category, question) based on the current stage and user emotion.
    Nervous emotions (fear, sad, surprise) trigger more calming questions.
    """
    state = "nervous" if emotion in ["fear", "sad", "surprise"] else "calm"
    pool = _QUESTIONS.get(stage, _QUESTIONS["Intro"])[state]
    return stage, random.choice(pool)

def get_follow_up(emotion: str) -> tuple[str, str]:
    """Generates a dynamic follow-up based on emotional state."""
    state = "nervous" if emotion in ["fear", "sad", "surprise"] else "calm"
    if state == "nervous":
        prompts = [
            "Take your time. Can you elaborate a bit more on that?",
            "That makes sense. Can you give a small example?",
            "No rush. How did that experience impact your next steps?"
        ]
    else:
        prompts = [
            "Interesting point. How would you scale that solution?",
            "Can you dive deeper into the technical trade-offs you made?",
            "What was the most challenging part of that specific situation?"
        ]
    return "Follow-up", random.choice(prompts)
