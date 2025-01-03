from pydantic import BaseModel, Field


class FinalAssessmentInput(BaseModel):
    Complex_Problem_Solving: int = Field(alias="Complex Problem Solving")
    Critical_Thinking: int = Field(alias="Critical Thinking")
    Mathematics: int = Field(alias="Mathematics")
    Science: int = Field(alias="Science")
    Learning_Strategy: int = Field(alias="Learning Strategy")
    Monitoring: int = Field(alias="Monitoring")
    Active_Listening: int = Field(alias="Active Listening")
    Social_Perceptiveness: int = Field(alias="Social Perceptiveness")
    Judgment_and_Decision_Making: int = Field(alias="Judgment and Decision Making")
    Instructing: int = Field(alias="Instructing")
    Active_Learning: int = Field(alias="Active Learning")
    Time_Management: int = Field(alias="Time Management")
    Writing: int = Field(alias="Writing")
    Speaking: int = Field(alias="Speaking")
    Reading_Comprehension: int = Field(alias="Reading Comprehension")
    The_Designer: int = Field(alias="The Designer")
    The_Visionary: int = Field(alias="The Visionary")
    The_Creator: int = Field(alias="The Creator")
    The_Creative_Builder: int = Field(alias="The Creative Builder")
    The_Inspirer: int = Field(alias="The Inspirer")
    The_Achiever: int = Field(alias="The Achiever")
    The_Analyst: int = Field(alias="The Analyst")
    The_Organizer: int = Field(alias="The Organizer")
    The_Coordinator: int = Field(alias="The Coordinator")
    The_Innovator: int = Field(alias="The Innovator")
    The_Leader: int = Field(alias="The Leader")
    The_Motivator: int = Field(alias="The Motivator")
    The_Explorer: int = Field(alias="The Explorer")
    The_Problem_Solver: int = Field(alias="The Problem-Solver")
    The_Supporter: int = Field(alias="The Supporter")
    Visual: int = Field(alias="Visual")
    Auditory: int = Field(alias="Auditory")
    Read_Write: int = Field(alias="Read/Write")
    Kinesthetic: int = Field(alias="Kinesthetic")
    Work_Life_Balance: int = Field(alias="Work-Life Balance")
    Teamwork_and_Collaboration: int = Field(alias="Teamwork and Collaboration")
    Stability_and_Security: int = Field(alias="Stability and Security")
    Social_Impact: int = Field(alias="Social Impact")
    Recognition_and_Achievement: int = Field(alias="Recognition and Achievement")
    Personal_Growth: int = Field(alias="Personal Growth")
    Leadership_and_Influence: int = Field(alias="Leadership and Influence")
    Independence_and_Flexibility: int = Field(alias="Independence and Flexibility")
    Helping_Others: int = Field(alias="Helping Others")
    Financial_Stability: int = Field(alias="Financial Stability")
    Creativity_and_Innovation: int = Field(alias="Creativity and Innovation")
    ENFJ: int = Field(alias="ENFJ")
    ENFP: int = Field(alias="ENFP")
    ENTJ: int = Field(alias="ENTJ")
    ENTP: int = Field(alias="ENTP")
    ESFJ: int = Field(alias="ESFJ")
    ESFP: int = Field(alias="ESFP")
    ESTJ: int = Field(alias="ESTJ")
    ESTP: int = Field(alias="ESTP")
    INFJ: int = Field(alias="INFJ")
    INFP: int = Field(alias="INFP")
    INTJ: int = Field(alias="INTJ")
    INTP: int = Field(alias="INTP")
    ISFJ: int = Field(alias="ISFJ")
    ISFP: int = Field(alias="ISFP")
    ISTJ: int = Field(alias="ISTJ")
    ISTP: int = Field(alias="ISTP")


class FinalAssessmentResponse(BaseModel):
    test_uuid: str
    test_name: str
    recommended_career: str
