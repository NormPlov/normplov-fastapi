from app.schemas.final_assessment import AllAssessmentsResponse


def prepare_model_input(response: AllAssessmentsResponse) -> dict:

    user_input_skills = {
        "Complex Problem Solving": 0,
        "Critical Thinking": 0,
        "Mathematics": 0,
        "Science": 0,
        "Learning Strategy": 0,
        "Monitoring": 0,
        "Active Listening": 0,
        "Social Perceptiveness": 0,
        "Judgment and Decision Making": 0,
        "Instructing": 0,
        "Active Learning": 0,
        "Time Management": 0,
        "Writing": 0,
        "Speaking": 0,
        "Reading Comprehension": 0,
        "The Designer": 0,
        "The Visionary": 0,
        "The Creator": 0,
        "The Creative Builder": 0,
        "The Inspirer": 0,
        "The Achiever": 0,
        "The Analyst": 0,
        "The Organizer": 0,
        "The Coordinator": 0,
        "The Innovator": 0,
        "The Leader": 0,
        "The Motivator": 0,
        "The Explorer": 0,
        "The Problem-Solver": 0,
        "The Supporter": 0,
        "Visual": 0,
        "Auditory": 0,
        "Read/Write": 0,
        "Kinesthetic": 0,
        "Work-Life Balance": 0,
        "Teamwork and Collaboration": 0,
        "Stability and Security": 0,
        "Social Impact": 0,
        "Recognition and Achievement": 0,
        "Personal Growth": 0,
        "Leadership and Influence": 0,
        "Independence and Flexibility": 0,
        "Helping Others": 0,
        "Financial Stability": 0,
        "Creativity and Innovation": 0,
        "ENFJ": 0,
        "ENFP": 0,
        "ENTJ": 0,
        "ENTP": 0,
        "ESFJ": 0,
        "ESFP": 0,
        "ESTJ": 0,
        "ESTP": 0,
        "INFJ": 0,
        "INFP": 0,
        "INTJ": 0,
        "INTP": 0,
        "ISFJ": 0,
        "ISFP": 0,
        "ISTJ": 0,
        "ISTP": 0,
    }

    if response.skill and response.skill.skills_grouped:
        for level, skills in response.skill.skills_grouped.items():
            for skill in skills:
                skill_name = skill.skill
                if skill_name in user_input_skills:
                    user_input_skills[skill_name] = 1

    if response.interest and response.interest.type_name:
        interest_type = response.interest.type_name
        if interest_type in user_input_skills:
            user_input_skills[interest_type] = 1

    if response.learning_style and response.learning_style.learning_style:
        learning_style = response.learning_style.learning_style
        if learning_style in user_input_skills:
            user_input_skills[learning_style] = 1

    if response.value and response.value.chart_data:
        for value in response.value.chart_data:
            label = value.label
            score = value.score
            if label in user_input_skills:
                user_input_skills[label] = 1 if score > 0 else 0

    if response.personality and response.personality.personality_type:
        personality_type = response.personality.personality_type.name
        if personality_type in user_input_skills:
            user_input_skills[personality_type] = 1

    return user_input_skills
