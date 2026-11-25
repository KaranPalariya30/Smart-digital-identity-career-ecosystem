"""
Skill prerequisite graph + learning-path ordering (DSA: DAG, DFS, Kahn's
topological sort with our own min-heap).

Given the skills a candidate is missing, we
  1. pull in every prerequisite they also lack      (DFS over the graph)
  2. order everything so prerequisites come first    (Kahn's algorithm)
  3. among skills that are ready, pick the most important first (min-heap)
"""
from .min_heap import MinHeap

# skill -> skills you should know first.  Names must be canonical (see skills_db).
PREREQS: dict[str, list[str]] = {
    "fastapi": ["python", "rest api"],
    "flask": ["python"],
    "django": ["python"],
    "pandas": ["python"],
    "numpy": ["python"],
    "pytest": ["python"],
    "airflow": ["python"],
    "celery": ["python"],
    "rest api": ["git"],
    "postgresql": ["sql"],
    "mysql": ["sql"],
    "mongodb": [],
    "kubernetes": ["docker", "linux"],
    "docker": ["linux"],
    "terraform": ["linux"],
    "ci/cd": ["git"],
    "github actions": ["git", "ci/cd"],
    "jenkins": ["ci/cd"],
    "react": ["javascript", "html", "css"],
    "next.js": ["react"],
    "redux": ["react"],
    "typescript": ["javascript"],
    "node.js": ["javascript"],
    "express": ["node.js"],
    "nestjs": ["node.js", "typescript"],
    "tailwind css": ["css"],
    "spring boot": ["java"],
    "machine learning": ["python", "numpy", "pandas"],
    "scikit-learn": ["machine learning"],
    "deep learning": ["machine learning"],
    "tensorflow": ["deep learning"],
    "pytorch": ["deep learning"],
    "keras": ["deep learning"],
    "nlp": ["machine learning"],
    "computer vision": ["deep learning"],
    "hugging face": ["deep learning", "nlp"],
    "generative ai": ["nlp", "python"],
    "langchain": ["generative ai", "python"],
    "rag": ["generative ai"],
    "spark": ["python", "sql"],
    "kafka": ["distributed systems"],
    "microservices": ["rest api", "docker"],
    "system design": ["data structures", "rest api"],
    "solidity": ["blockchain", "javascript"],
    "smart contracts": ["solidity"],
}


def _collect_closure(targets: set[str], have: set[str]) -> set[str]:
    """DFS: targets + all transitive prerequisites that the candidate lacks."""
    need: set[str] = set()
    stack = [t for t in targets if t not in have]
    while stack:
        skill = stack.pop()
        if skill in need:
            continue
        need.add(skill)
        stack.extend(p for p in PREREQS.get(skill, []) if p not in have and p not in need)
    return need


def learning_order(missing_weights: dict[str, float], have: set[str], max_steps: int = 10) -> list[dict]:
    """
    missing_weights: {missing skill: importance}   have: skills already on the resume
    Returns [{"order": 1, "skill": ..., "kind": "prerequisite"|"target"}, ...]
    """
    need = _collect_closure(set(missing_weights), have)

    indegree = {s: 0 for s in need}
    children: dict[str, list[str]] = {s: [] for s in need}
    for s in need:
        for p in PREREQS.get(s, []):
            if p in need:
                indegree[s] += 1
                children[p].append(s)

    def priority(s: str):
        # higher importance first; prerequisites that unlock many skills also rank well
        return (-(missing_weights.get(s, 0.0) + 0.1 * len(children[s])), s)

    heap = MinHeap(priority(s) for s in need if indegree[s] == 0)   # O(n) heapify

    order: list[str] = []
    while heap:
        _, s = heap.pop()
        order.append(s)
        for c in children[s]:
            indegree[c] -= 1
            if indegree[c] == 0:
                heap.push(priority(c))

    if len(order) != len(need):            # cycle in PREREQS: should never happen (tested)
        raise ValueError("Cycle detected in skill prerequisite graph")

    return [
        {"order": i + 1, "skill": s,
         "kind": "target" if s in missing_weights else "prerequisite"}
        for i, s in enumerate(order[:max_steps])
    ]
