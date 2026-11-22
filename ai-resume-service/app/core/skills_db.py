"""
Skill knowledge base: canonical skills, categories and aliases.

Why aliases: "Postgres", "PostgreSQL" and "psql" are one skill. Matching on
canonical names lets the scorer treat them as equal.

AMBIGUOUS patterns ("c", "r", "go", "rest") are real words/letters in normal
English, so they only count when they appear in a list-like context such as
"Languages: Python, C, Go".
"""

# category -> { canonical skill: [aliases] }
SKILLS: dict[str, dict[str, list[str]]] = {
    "programming_languages": {
        "python": ["python3", "py"],
        "java": [],
        "javascript": ["js", "ecmascript", "es6"],
        "typescript": ["ts"],
        "c++": ["cpp"],
        "c": [],
        "c#": ["csharp", "c sharp"],
        "go": ["golang"],
        "rust": [],
        "ruby": [],
        "php": [],
        "swift": [],
        "kotlin": [],
        "scala": [],
        "r": [],
        "matlab": [],
        "bash": ["shell scripting", "shell"],
        "dart": [],
        "sql": ["t-sql", "pl/sql", "plsql"],
        "html": ["html5"],
        "css": ["css3"],
    },
    "web_frameworks": {
        "flask": [],
        "fastapi": ["fast api"],
        "django": [],
        "express": ["express.js", "expressjs"],
        "node.js": ["nodejs", "node js", "node"],
        "spring boot": ["springboot", "spring"],
        "react": ["reactjs", "react.js"],
        "angular": ["angularjs"],
        "vue": ["vuejs", "vue.js"],
        "next.js": ["nextjs"],
        "nuxt": [],
        "rails": ["ruby on rails"],
        "laravel": [],
        "nestjs": ["nest.js"],
        "asp.net": ["asp.net core"],
        "flutter": [],
        "tailwind css": ["tailwind", "tailwindcss"],
        "redux": [],
    },
    "databases": {
        "mysql": [],
        "postgresql": ["postgres", "psql"],
        "mongodb": ["mongo"],
        "redis": [],
        "sqlite": [],
        "cassandra": [],
        "elasticsearch": ["elastic search"],
        "dynamodb": [],
        "neo4j": [],
        "mariadb": [],
        "oracle": ["oracle db"],
        "sql server": ["mssql", "ms sql"],
        "firebase": [],
    },
    "cloud_devops": {
        "aws": ["amazon web services"],
        "gcp": ["google cloud", "google cloud platform"],
        "azure": ["microsoft azure"],
        "docker": [],
        "kubernetes": ["k8s"],
        "terraform": [],
        "ansible": [],
        "jenkins": [],
        "github actions": [],
        "gitlab ci": ["gitlab ci/cd"],
        "ci/cd": ["cicd", "ci cd", "continuous integration", "continuous delivery"],
        "nginx": [],
        "linux": ["ubuntu", "debian"],
        "helm": [],
        "prometheus": [],
        "grafana": [],
    },
    "ai_ml": {
        "machine learning": ["ml"],
        "deep learning": [],
        "neural networks": ["neural network"],
        "nlp": ["natural language processing"],
        "computer vision": [],
        "scikit-learn": ["scikit learn", "sklearn", "scikit"],
        "tensorflow": [],
        "pytorch": ["torch"],
        "keras": [],
        "xgboost": [],
        "pandas": [],
        "numpy": [],
        "matplotlib": [],
        "hugging face": ["huggingface", "transformers"],
        "generative ai": ["genai", "gen ai", "llm", "llms", "large language models"],
        "langchain": [],
        "rag": ["retrieval augmented generation"],
        "reinforcement learning": [],
        "data science": [],
        "tableau": [],
        "power bi": ["powerbi"],
    },
    "tools_misc": {
        "git": [],
        "github": [],
        "jira": [],
        "postman": [],
        "graphql": [],
        "rest api": ["rest apis", "restful", "restful api", "restful apis", "rest", "rest-api"],
        "grpc": [],
        "websocket": ["websockets"],
        "celery": [],
        "kafka": [],
        "rabbitmq": [],
        "airflow": [],
        "spark": ["pyspark", "apache spark"],
        "hadoop": [],
        "opencv": [],
        "selenium": [],
        "pytest": [],
        "jest": [],
        "webpack": [],
        "blockchain": [],
        "solidity": [],
        "smart contracts": ["smart contract"],
    },
    "concepts": {
        "oop": ["object oriented", "object-oriented"],
        "data structures": [],
        "algorithms": [],
        "dsa": [],
        "design patterns": [],
        "microservices": ["microservice"],
        "agile": ["scrum"],
        "tdd": ["test driven development"],
        "system design": [],
        "distributed systems": [],
        "concurrency": [],
        "etl": [],
        "data pipelines": ["data pipeline"],
        "big data": [],
        "unit testing": [],
    },
}

# Patterns that are also ordinary words / single letters.
AMBIGUOUS_PATTERNS: frozenset[str] = frozenset({"c", "r", "go", "rest", "py", "node", "spring", "shell", "torch"})

# ---- derived lookups (built once at import) ---------------------------------
CANONICAL_CATEGORY: dict[str, str] = {}
PATTERN_TO_CANONICAL: dict[str, str] = {}

for _cat, _skills in SKILLS.items():
    for _canon, _aliases in _skills.items():
        CANONICAL_CATEGORY[_canon] = _cat
        PATTERN_TO_CANONICAL[_canon] = _canon
        for _alias in _aliases:
            PATTERN_TO_CANONICAL[_alias] = _canon

ALL_SKILLS: frozenset[str] = frozenset(CANONICAL_CATEGORY)
