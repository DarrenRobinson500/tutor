
from maths_engine import evaluate_int_expression
def assess_ans(ans):
    if "logic" in ans:
        condition = ans["logic"]
        try:
            is_true = evaluate_int_expression(condition, generated_params)
        except Exception:
            is_true = False

        # Mark correct only if BOTH:
        # 1. YAML says correct: true
        # 2. Condition evaluates to true
        answers.append({
            "text": ans.get("text", ""),
            "correct": ans.get("correct", False) and is_true
        })


ans = {
    "logic": "a > b",
    "text": "Pizza",
    "correct": "true"
  },

print(ans["logic"])
