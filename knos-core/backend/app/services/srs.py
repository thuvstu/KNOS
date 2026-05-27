# backend/app/services/srs.py
"""SuperMemo Algorithm SM-2 (1987) 実装"""
from datetime import date, timedelta
from dataclasses import dataclass


@dataclass
class SrsState:
    ease_factor: float = 2.5
    interval: int = 1    # 次回まで何日か
    repetitions: int = 0


def sm2_review(state: SrsState, grade: int) -> tuple[SrsState, date]:
    """
    grade: 0-5
      0: 完全に忘れた
      1: 難しくて間違えた
      2: 難しかったが正解
      3: 少し難しかったが正解
      4: 簡単に正解
      5: 完璧

    Returns: (new_state, next_review_date)
    """
    if grade < 3:
        # 失敗: リセット
        new_state = SrsState(
            ease_factor=max(1.3, state.ease_factor - 0.2),
            interval=1,
            repetitions=0,
        )
    else:
        if state.repetitions == 0:
            interval = 1
        elif state.repetitions == 1:
            interval = 6
        else:
            interval = round(state.interval * state.ease_factor)

        new_ef = state.ease_factor + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
        new_state = SrsState(
            ease_factor=max(1.3, new_ef),
            interval=interval,
            repetitions=state.repetitions + 1,
        )

    next_date = date.today() + timedelta(days=new_state.interval)
    return new_state, next_date
