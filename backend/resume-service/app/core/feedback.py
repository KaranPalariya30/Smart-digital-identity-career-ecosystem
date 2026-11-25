"""Rule-based feedback (v1 logic, adapted to v2 result shapes)."""


def verdict(score: int, skill_pct: float) -> str:
    if score >= 80 and skill_pct >= 70:
        return "Strong match - submit with confidence."
    if score >= 80:
        return "High similarity but skill gaps exist - address missing skills first."
    if score >= 60 and skill_pct >= 50:
        return "Decent match - with targeted edits this could be a strong application."
    if score >= 60:
        return "Moderate match - rewrite some bullets using the role's terminology."
    if score >= 40:
        return "Weak match - significant tailoring needed before applying."
    return "Poor match - consider whether this role fits your current profile."


def generate_feedback(score: int, skill_pct: float, matched_skills: list[str],
                      missing_skills: list[str], missing_keywords: list[str],
                      matched_keyword_count: int, verified_pct: float | None) -> dict:
    strengths, improvements, tips = [], [], []

    if score >= 70:
        strengths.append("Your resume language closely matches this role.")
    if matched_skills:
        strengths.append(f"Key matched skills: {', '.join(matched_skills[:3])}.")
    if skill_pct >= 60:
        strengths.append(f"You cover {skill_pct}% of the skills this role asks for.")
    if matched_keyword_count >= 10:
        strengths.append("High keyword overlap - good chance of passing ATS filters.")
    if verified_pct:
        strengths.append(f"{verified_pct}% of your matched skills are credential-verified.")
    if not strengths:
        strengths.append("You have some foundational skills that partially align.")

    if missing_skills:
        improvements.append(
            f"Add these skills if you have them: {', '.join(missing_skills[:4])}.")
    if score < 50:
        improvements.append("Rewrite your bullets using terms from the role description.")
    if skill_pct < 40:
        improvements.append(
            f"You match only {skill_pct}% of the skills. Consider upskilling or targeting a better-fit role.")
    if missing_keywords:
        improvements.append(
            f"These keywords are absent from your resume: {', '.join(missing_keywords[:5])}.")

    tips.append("Tailor your resume for each role instead of using one generic version.")
    if score < 60:
        tips.append("Start bullets with action verbs: Built, Designed, Implemented, Optimized.")
    if missing_skills:
        tips.append("Academic and personal projects count - add them if they use the missing skills.")
    tips.append("Quantify results: '3x faster', '40% reduction', '10k users'.")

    return {"strengths": strengths, "improvements": improvements, "tips": tips,
            "verdict": verdict(score, skill_pct)}
