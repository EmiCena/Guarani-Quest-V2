import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

from learning.models import GlossaryEntry, SRSDeck, Flashcard

User = get_user_model()

def guess_delimiter(sample: str) -> str:
    for d in [",", ";", "\t", "|"]:
        if d in sample:
            return d
    return ","

class Command(BaseCommand):
    help = "Import glossary entries from CSV and create SRS flashcards. CSV headers: es,gn[,notes]"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to CSV (UTF-8 or UTF-8-SIG)")
        parser.add_argument("--user", required=True, help="Username that will own the entries")
        parser.add_argument("--deck", default="Mi Glosario", help="Deck name (default: Mi Glosario)")
        parser.add_argument("--delimiter", default=None, help="Optional delimiter (, ; \\t |). If not set, tries to guess.")
        parser.add_argument("--update-notes", action="store_true", help="Update notes when the entry already exists")

    def handle(self, *args, **opts):
        csv_path = Path(opts["csv_file"]).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        try:
            user = User.objects.get(username=opts["user"])
        except User.DoesNotExist:
            raise CommandError(f"User not found: {opts['user']}")

        deck, _ = SRSDeck.objects.get_or_create(user=user, name=opts["deck"])
        self.stdout.write(self.style.NOTICE(f"Using deck: {deck.name}"))

        # Read CSV
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            sample = f.read(4096)
            f.seek(0)
            delim = opts["delimiter"] or guess_delimiter(sample)
            reader = csv.DictReader(f, delimiter=delim)
            headers = [h.strip().lower() for h in (reader.fieldnames or [])]
            # Map possible header names
            def pick(*names):
                for n in names:
                    if n in headers:
                        return n
                return None
            col_es = pick("es", "spanish", "español", "source", "front")
            col_gn = pick("gn", "guarani", "guaraní", "target", "back")
            col_notes = pick("notes", "nota", "notas", "comment")

            if not col_es or not col_gn:
                raise CommandError("CSV must contain headers for ES and GN (e.g., es,gn[,notes])")

            created_entries = 0
            updated_entries = 0
            created_cards = 0
            skipped = 0

            for row in reader:
                es = (row.get(col_es) or "").strip()
                gn = (row.get(col_gn) or "").strip()
                notes = (row.get(col_notes) or "").strip() if col_notes else ""
                if not es or not gn:
                    skipped += 1
                    continue

                ge, made = GlossaryEntry.objects.get_or_create(
                    user=user, source_text_es=es, translated_text_gn=gn,
                    defaults={"notes": notes}
                )
                if made:
                    created_entries += 1
                else:
                    if opts["update-notes"] and notes:
                        ge.notes = notes
                        ge.save(update_fields=["notes"])
                        updated_entries += 1

                # Ensure card exists
                if not Flashcard.objects.filter(user=user, deck=deck, front_text_es=es, back_text_gn=gn).exists():
                    Flashcard.objects.create(
                        user=user, deck=deck,
                        front_text_es=es, back_text_gn=gn, notes=notes,
                        due_at=timezone.now()
                    )
                    created_cards += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Glossary: +{created_entries} created, {updated_entries} updated, {skipped} skipped. "
            f"SRS cards created: {created_cards}"
        ))