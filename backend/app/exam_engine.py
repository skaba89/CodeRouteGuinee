def score_answers(answer_key: dict[str, str], submitted_answers: dict[str, str]) -> dict:
    total = len(answer_key)
    correct = sum(1 for question_id, expected in answer_key.items() if submitted_answers.get(question_id) == expected)
    score_percent = round((correct / total) * 100, 2) if total else 0
    return {
        "total_questions": total,
        "correct_answers": correct,
        "wrong_answers": total - correct,
        "score_percent": score_percent,
        "passed": correct >= 35 if total == 40 else score_percent >= 87.5,
    }
