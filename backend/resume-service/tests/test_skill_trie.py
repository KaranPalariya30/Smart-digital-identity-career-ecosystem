from app.core.skill_trie import AhoCorasick, matcher


def skills(text):
    return set(matcher.count(text))


def test_aho_corasick_classic():
    ac = AhoCorasick(["he", "she", "his", "hers"])
    found = {p for _, _, p in ac.search("ushers")}
    assert found == {"she", "he", "hers"}


def test_basic_and_aliases():
    s = skills("Built APIs with FastAPI and Postgres, deployed on K8s and GCP.")
    assert {"fastapi", "postgresql", "kubernetes", "gcp"} <= s


def test_word_boundaries():
    assert "java" not in skills("Strong JavaScript skills")
    assert "javascript" in skills("Strong JavaScript skills")
    assert "c" not in skills("Worked in scrum teams on a database project")


def test_special_character_skills():
    s = skills("Languages: C++, C#, Python")
    assert {"c++", "c#", "python"} <= s
    assert "c" not in s          # 'c' inside 'c++' / 'c#' must not double count
    assert "ci/cd" in skills("Set up CI/CD pipelines")


def test_longest_match_wins():
    s = skills("Designed REST APIs")
    assert "rest api" in s


def test_ambiguous_only_in_list_context():
    assert "go" not in skills("Ready to go to market with the team")
    assert "go" in skills("Languages: Python, Go, Rust")
    assert "r" in skills("Skills: Python, R, SQL")
    assert "r" not in skills("I worked on research and reporting")


def test_multiword_across_line_wrap():
    assert "machine learning" in skills("experience in machine\nlearning projects")


def test_counts():
    c = matcher.count("Python, python and PYTHON")
    assert c["python"] == 3
