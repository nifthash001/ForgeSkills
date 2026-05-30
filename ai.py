import ast
import json
import re


def _try_parse_json(content):
    try:
        return json.loads(content)
    except Exception:
        try:
            return ast.literal_eval(content)
        except Exception:
            return None


def _extract_json_array(content):
    if not isinstance(content, str):
        return None

    start = content.find('[')
    end = content.rfind(']')
    if start != -1 and end != -1 and end > start:
        return _try_parse_json(content[start:end + 1])
    return None


def _parse_plain_text_to_roadmap(content, topic):
    if not isinstance(content, str):
        return [{"title": topic, "estimate": "", "subtasks": [str(content)]}]

    text = content.strip()
    if not text:
        return [{"title": topic, "estimate": "", "subtasks": []}]

    section_pattern = re.compile(r'(?ms)^\s*(\d+)[\.\)]\s*(.+?)(?=^\s*\d+[\.\)]\s+|\Z)')
    sections = section_pattern.findall(text)
    if sections:
        steps = []
        for _, section_text in sections:
            section_text = section_text.strip()
            section_lines = [line.strip() for line in section_text.splitlines() if line.strip()]
            if not section_lines:
                continue
            title = section_lines[0]
            subtasks = []
            for sub_line in section_lines[1:]:
                bullet_match = re.match(r'^[\-\*\u2022]\s*(.+)', sub_line)
                if bullet_match:
                    subtasks.append(bullet_match.group(1).strip())
                else:
                    subtasks.append(sub_line)
            steps.append({"title": title, "estimate": "", "subtasks": subtasks})
        return steps

    bullet_lines = re.findall(r'(?m)^[\-\*\u2022]\s*(.+)$', text)
    if bullet_lines:
        return [{"title": topic, "estimate": "", "subtasks": bullet_lines}]

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return [{"title": line, "estimate": "", "subtasks": []} for line in lines]


def _is_raw_text_step(item):
    if not isinstance(item, dict):
        return False

    subtasks = item.get("subtasks")
    if isinstance(subtasks, list) and len(subtasks) == 1 and isinstance(subtasks[0], str):
        text = subtasks[0].strip()
        if len(text) > 80 and ("\n" in text or re.search(r'(?m)^\s*\d+[\.\)]\s+', text) or re.search(r'(?m)^[\-\*\u2022]\s+', text)):
            return True
    return False


def _explode_raw_text_step(item, topic):
    if not _is_raw_text_step(item):
        return [item]

    raw_text = item["subtasks"][0].strip()
    title = item.get("title") or topic
    parsed_steps = _parse_plain_text_to_roadmap(raw_text, title)

    if len(parsed_steps) > 1:
        return parsed_steps

    if parsed_steps and parsed_steps[0].get("title", "") != title:
        return parsed_steps

    return [item]


def _normalize_roadmap(parsed, topic):
    if isinstance(parsed, dict):
        parsed = [parsed]

    if isinstance(parsed, list):
        normalized = []
        for item in parsed:
            if isinstance(item, dict):
                expanded = _explode_raw_text_step(item, topic)
                normalized.extend(expanded)
            else:
                normalized.append({"title": str(item), "estimate": "", "subtasks": []})
        return normalized

    return _parse_plain_text_to_roadmap(parsed or topic, topic)


try:
    import ollama

    def generate_roadmap(topic):
        prompt = f"""
        Produce a concise learning roadmap for the topic below.

        Requirements:
        - Output ONLY valid JSON (no explanation)
        - JSON must be a list of objects. Each object should contain:
          - "title": short step title (string)
          - "estimate": short time estimate (string, optional)
          - "subtasks": list of 2-5 short actionable subtasks (strings)

        Example output:
        [
          {{"title": "Learn basics", "estimate": "2 hours", "subtasks": ["Read intro", "Try examples"]}},
          {{"title": "Build project", "estimate": "4 hours", "subtasks": ["Plan", "Implement core features"]}}
        ]

        Topic: {topic}
        """.strip()

        response = ollama.chat(
            model='qwen:4b',
            messages=[{'role': 'user', 'content': prompt}]
        )

        content = response['message']['content']
        parsed = _try_parse_json(content)
        if parsed is None:
            parsed = _extract_json_array(content)
        if parsed is None:
            parsed = _parse_plain_text_to_roadmap(content, topic)

        return _normalize_roadmap(parsed, topic)

except Exception:
    # Fallback for environments without ollama — useful for local UI testing
    def generate_roadmap(topic):
        return [
            {
                "title": "Understand the basics",
                "estimate": "2 hours",
                "subtasks": [
                    "Read an introductory article",
                    "Watch a short tutorial",
                    "Try a simple example",
                ],
            },
            {
                "title": "Build a small project",
                "estimate": "4 hours",
                "subtasks": [
                    "Plan the features",
                    "Implement core functionality",
                    "Test and iterate",
                ],
            },
            {
                "title": "Practice with exercises",
                "estimate": "3 hours",
                "subtasks": [
                    "Solve curated problems",
                    "Refactor for clarity",
                ],
            },
        ]