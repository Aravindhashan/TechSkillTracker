import urllib.parse


def get_youtube_search_url(skill_name):
    """Generate YouTube search URL for a skill"""
    query = f"{skill_name} tutorial beginner"
    encoded_query = urllib.parse.quote(query)
    return f"https://www.youtube.com/results?search_query={encoded_query}"


def get_learning_resources(skill_name):
    """
    Generate learning resource links for a given skill
    Returns a dictionary with platform names and URLs
    """
    skill_encoded = urllib.parse.quote(skill_name)

    resources = {
        "YouTube": {
            "url": f"https://www.youtube.com/results?search_query={skill_encoded}+tutorial",
            "icon": "🎥",
            "description": "Free video tutorials"
        },
        "Udemy": {
            "url": f"https://www.udemy.com/courses/search/?q={skill_encoded}",
            "icon": "📚",
            "description": "Paid courses with certificates"
        },
        "Coursera": {
            "url": f"https://www.coursera.org/search?query={skill_encoded}",
            "icon": "🎓",
            "description": "University-level courses"
        },
        "freeCodeCamp": {
            "url": f"https://www.freecodecamp.org/news/search/?query={skill_encoded}",
            "icon": "💻",
            "description": "Free coding tutorials and articles"
        },
        "GeeksforGeeks": {
            "url": f"https://www.geeksforgeeks.org/{skill_encoded.lower()}-tutorial/",
            "icon": "📖",
            "description": "Programming tutorials and practice"
        },
        "W3Schools": {
            "url": f"https://www.w3schools.com/search/search.asp?q={skill_encoded}",
            "icon": "🌐",
            "description": "Interactive web tutorials"
        }
    }

    return resources


def get_skill_specific_resources(skill_name):
    """
    Get curated resources for specific popular skills
    """
    skill_lower = skill_name.lower()

    # Curated resources for popular skills
    specific_resources = {
        "python": [
            {"name": "Python Official Tutorial", "url": "https://docs.python.org/3/tutorial/", "type": "Documentation"},
            {"name": "Automate the Boring Stuff", "url": "https://automatetheboringstuff.com/", "type": "Free Book"},
            {"name": "Real Python", "url": "https://realpython.com/", "type": "Tutorials"},
        ],
        "javascript": [
            {"name": "JavaScript.info", "url": "https://javascript.info/", "type": "Tutorial"},
            {"name": "MDN Web Docs", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript", "type": "Documentation"},
            {"name": "Eloquent JavaScript", "url": "https://eloquentjavascript.net/", "type": "Free Book"},
        ],
        "react": [
            {"name": "React Official Docs", "url": "https://react.dev/", "type": "Documentation"},
            {"name": "React Tutorial", "url": "https://react.dev/learn", "type": "Tutorial"},
        ],
        "sql": [
            {"name": "SQLBolt", "url": "https://sqlbolt.com/", "type": "Interactive Tutorial"},
            {"name": "SQL Zoo", "url": "https://sqlzoo.net/", "type": "Practice"},
            {"name": "W3Schools SQL", "url": "https://www.w3schools.com/sql/", "type": "Tutorial"},
        ],
        "java": [
            {"name": "Java Official Tutorial", "url": "https://docs.oracle.com/javase/tutorial/", "type": "Documentation"},
            {"name": "Java Programming MOOC", "url": "https://java-programming.mooc.fi/", "type": "Free Course"},
        ],
        "machine learning": [
            {"name": "Google ML Crash Course", "url": "https://developers.google.com/machine-learning/crash-course", "type": "Free Course"},
            {"name": "Fast.ai", "url": "https://www.fast.ai/", "type": "Free Course"},
            {"name": "Kaggle Learn", "url": "https://www.kaggle.com/learn", "type": "Interactive"},
        ],
        "data science": [
            {"name": "Kaggle Learn", "url": "https://www.kaggle.com/learn", "type": "Interactive"},
            {"name": "DataCamp", "url": "https://www.datacamp.com/", "type": "Courses"},
        ],
        "aws": [
            {"name": "AWS Free Tier", "url": "https://aws.amazon.com/free/", "type": "Practice"},
            {"name": "AWS Training", "url": "https://aws.amazon.com/training/", "type": "Official Training"},
        ],
        "docker": [
            {"name": "Docker Official Tutorial", "url": "https://docs.docker.com/get-started/", "type": "Documentation"},
            {"name": "Play with Docker", "url": "https://labs.play-with-docker.com/", "type": "Interactive"},
        ],
        "git": [
            {"name": "Git Official Book", "url": "https://git-scm.com/book/en/v2", "type": "Free Book"},
            {"name": "Learn Git Branching", "url": "https://learngitbranching.js.org/", "type": "Interactive"},
        ],
    }

    # Return specific resources if available
    for key in specific_resources:
        if key in skill_lower or skill_lower in key:
            return specific_resources[key]

    return []


def get_learning_path_with_resources(missing_skills):
    """
    Build a structured learning path with resources for multiple skills.

    Returns a list of dicts (one per skill). Each entry has:
    step, skill, youtube_url, specific_resources (list or []), platform_resources (dict),
    timeline (str), tips (list of str).
    """
    path = []
    for idx, skill in enumerate(missing_skills, 1):
        path.append(
            {
                "step": idx,
                "skill": skill,
                "youtube_url": get_youtube_search_url(skill),
                "specific_resources": get_skill_specific_resources(skill),
                "platform_resources": get_learning_resources(skill),
                "timeline": "Beginner: 2-4 weeks; Intermediate: 2-3 months",
                "tips": [
                    "Start with YouTube basics",
                    "Practice daily (1-2 hours)",
                    "Build small projects",
                    "Join online communities",
                ],
            }
        )
    return path
