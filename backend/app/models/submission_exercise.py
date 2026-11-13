"""
Submission OOP Exercise
Demonstrates Python OOP concepts: classes, instances, __init__ constructor,
attributes (self.submission_id, etc.), and methods (check_similarity).
"""

class Submission:
    def __init__(self, submission_id: str, learner_id: int, assessment_name: str, similarity_score: float):
        self.submission_id = submission_id
        self.learner_id = learner_id
        self.assessment_name = assessment_name
        self.similarity_score = similarity_score

    def check_similarity(self) -> str:
        """
        Evaluates the similarity score against business policy thresholds:
        - Score < 20: NO_FLAG
        - 20 <= Score < 70: REVIEW_REQUIRED
        - Score >= 70: PRIORITY_REVIEW
        """
        if self.similarity_score < 20.0:
            return "NO_FLAG"
        elif self.similarity_score < 70.0:
            return "REVIEW_REQUIRED"
        else:
            return "PRIORITY_REVIEW"

    def __repr__(self) -> str:
        return (f"Submission(id='{self.submission_id}', learner={self.learner_id}, "
                f"assessment='{self.assessment_name}', score={self.similarity_score}%, "
                f"flag={self.check_similarity()})")


if __name__ == "__main__":
    # Test cases to verify the logic
    sub1 = Submission("SUB-2026-000001", 101, "Intro to Computer Science", 14.5)
    sub2 = Submission("SUB-2026-000002", 102, "Data Structures Final", 45.0)
    sub3 = Submission("SUB-2026-000003", 103, "Algorithms Lab 3", 85.0)

    print(f"{sub1} -> {sub1.check_similarity()}")
    print(f"{sub2} -> {sub2.check_similarity()}")
    print(f"{sub3} -> {sub3.check_similarity()}")

