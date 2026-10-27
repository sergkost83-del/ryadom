from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.communities.models import Building, Community, Locality, Region, Street
from apps.communities.seed import DEFAULT_SEED, SeedError, load_seed_file


class Command(BaseCommand):
    help = "Загружает справочник ЖК и домов из JSON. Безопасно запускать повторно."

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DEFAULT_SEED), help="Путь к JSON со справочником")

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            records = load_seed_file(options["file"])
        except (SeedError, OSError, ValueError) as exc:
            raise CommandError(f"Справочник не загружен: {exc}") from exc

        for rec in records:
            region, _ = Region.objects.get_or_create(name=rec.region)
            locality, _ = Locality.objects.get_or_create(region=region, name=rec.locality)
            community, _ = Community.objects.update_or_create(
                locality=locality, slug=rec.community_slug, defaults={"name": rec.community_name}
            )
            street, _ = Street.objects.get_or_create(community=community, name=rec.street)
            Building.objects.update_or_create(street=street, slug=rec.slug, defaults={"label": rec.label})

        self.stdout.write(
            self.style.SUCCESS(
                f"Справочник загружен: ЖК {Community.objects.count()}, домов {Building.objects.count()}."
            )
        )
