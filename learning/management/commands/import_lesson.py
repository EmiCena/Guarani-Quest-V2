# learning/management/commands/import_lesson.py
import json
import os
from pathlib import Path
from copy import deepcopy

from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from django.db import transaction

from learning.models import (
    Lesson, LessonSection,
    FillBlankExercise, MultipleChoiceExercise,
    MatchingExercise, MatchingPair,
    PronunciationExercise,
)

try:
    import yaml  # optional for .yml/.yaml
    HAS_YAML = True
except Exception:
    HAS_YAML = False


def _auto_letter_choices(choices):
    # Accept either [{"key":"A","text":"..."}, ...] or ["text A", "text B", ...]
    out = []
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i, item in enumerate(choices):
        if isinstance(item, dict) and "key" in item and "text" in item:
            out.append({"key": str(item["key"]).upper(), "text": str(item["text"])})
        else:
            out.append({"key": letters[i], "text": str(item)})
    return out


class Command(BaseCommand):
    help = "Import a lesson from JSON or YAML. See README sample format."

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="Path to lesson.json or lesson.yaml")
        parser.add_argument("--order", type=int, default=None, help="Optional lesson order")
        parser.add_argument("--publish", action="store_true", help="Set is_published=True")
        parser.add_argument("--media-base", type=str, default=".", help="Base folder to resolve audio file paths")

    def handle(self, *args, **opts):
        path = Path(opts["file"]).expanduser().resolve()
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        # Load
        if path.suffix.lower() in [".yml", ".yaml"]:
            if not HAS_YAML:
                raise CommandError("PyYAML not installed. pip install pyyaml")
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        else:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        title = (data.get("title") or "").strip()
        if not title:
            raise CommandError("Missing lesson 'title'")
        description = data.get("description", "") or ""
        order = opts["order"] if opts["order"] is not None else int(data.get("order") or 0)
        is_published = bool(opts["publish"] or data.get("is_published"))

        sections = data.get("sections", []) or []
        fillblanks = data.get("fillblanks", []) or []
        mcqs = data.get("mcqs", []) or []
        matchings = data.get("matching", []) or []
        pronun = data.get("pronunciation", []) or []

        media_base = Path(opts["media-base"]).expanduser().resolve()

        with transaction.atomic():
            lesson = Lesson.objects.create(
                title=title,
                description=description,
                order=order,
                is_published=is_published,
            )
            self.stdout.write(self.style.NOTICE(f"Created lesson: {lesson}"))

            # Sections
            for i, s in enumerate(sections):
                sec = LessonSection.objects.create(
                    lesson=lesson,
                    title=s.get("title", "") or "",
                    body=s.get("body", "") or "",
                    order=int(s.get("order") or i),
                )
                ref_path = s.get("reference_audio")
                if ref_path:
                    full = (media_base / ref_path).resolve()
                    if full.exists():
                        with open(full, "rb") as f:
                            sec.reference_audio.save(os.path.basename(full), File(f), save=True)

            # Fill blanks
            for i, fb in enumerate(fillblanks):
                FillBlankExercise.objects.create(
                    lesson=lesson,
                    prompt_text=fb["prompt_text"],
                    correct_answer=fb["correct_answer"],
                    order=int(fb.get("order") or i),
                )

            # MCQs
            for i, q in enumerate(mcqs):
                choices = _auto_letter_choices(q.get("choices") or q.get("options") or [])
                MultipleChoiceExercise.objects.create(
                    lesson=lesson,
                    question_text=q["question_text"],
                    choices_json=choices,
                    correct_key=str(q["correct_key"]).upper(),
                    order=int(q.get("order") or i),
                )

            # Matching (each block is a separate exercise)
            for i, m in enumerate(matchings):
                mex = MatchingExercise.objects.create(
                    lesson=lesson,
                    instructions=m.get("instructions") or "Relaciona las parejas",
                    order=int(m.get("order") or i),
                )
                for pair in m.get("pairs", []):
                    MatchingPair.objects.create(
                        exercise=mex,
                        left_text=pair["left"],
                        right_text=pair["right"],
                    )

            # Pronunciation
            for i, p in enumerate(pronun):
                pe = PronunciationExercise.objects.create(
                    lesson=lesson,
                    text_guarani=p["text_guarani"],
                    order=int(p.get("order") or i),
                )
                ref = p.get("reference_audio")
                if ref:
                    full = (media_base / ref).resolve()
                    if full.exists():
                        with open(full, "rb") as f:
                            pe.reference_audio.save(os.path.basename(full), File(f), save=True)

        self.stdout.write(self.style.SUCCESS("Lesson import completed."))