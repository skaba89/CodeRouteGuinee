from app.exam_engine import score_answers


def test_score_answers_passes_when_threshold_is_reached() -> None:
    answer_key = {str(index): "A" for index in range(40)}
    submitted = {str(index): "A" for index in range(35)}
    submitted.update({str(index): "B" for index in range(35, 40)})

    result = score_answers(answer_key, submitted)

    assert result["total_questions"] == 40
    assert result["correct_answers"] == 35
    assert result["wrong_answers"] == 5
    assert result["passed"] is True


def test_score_answers_fails_below_threshold() -> None:
    answer_key = {str(index): "A" for index in range(40)}
    submitted = {str(index): "A" for index in range(34)}
    submitted.update({str(index): "B" for index in range(34, 40)})

    result = score_answers(answer_key, submitted)

    assert result["correct_answers"] == 34
    assert result["passed"] is False
