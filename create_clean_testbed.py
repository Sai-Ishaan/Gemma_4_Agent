from pathlib import Path

CLEAN_REPO_DIR = Path("./clean_repo")

FILES = {
    "src/__init__.py": "",
    "src/math_ops.py": '''def calculate_discount(price: float, discount_rate: float) -> float:
    if price < 0 or not (0.0 <= discount_rate <= 1.0):
        raise ValueError("Invalid price or discount rate")
    return price * (1.0 - discount_rate)
''',
    "tests/__init__.py": "",
    "tests/test_math.py": '''import unittest
from src.math_ops import calculate_discount

class TestMathOps(unittest.TestCase):
    def test_calculate_discount_valid(self):
        self.assertAlmostEqual(calculate_discount(100.0, 0.2), 80.0)

if __name__ == "__main__":
    unittest.main()
'''
}

for rel_path, content in FILES.items():
    file_path = CLEAN_REPO_DIR / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

print("Created clean_repo successfully!")