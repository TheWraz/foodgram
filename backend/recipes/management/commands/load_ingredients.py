import csv
import os

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    """Загружает ингридиенты из CSV файла."""

    def handle(self, *args, **options):
        csv_file = 'data/ingredients.csv'

        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'Файл {csv_file} не найден'))
            return

        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=',')
            count = 0

            for name, unit in reader:
                ingredient, created = Ingredient.objects.get_or_create(
                    name=name.strip(),
                    measurement_unit=unit.strip()
                )

                if created:
                    count += 1

            print(f'Загружено {count} ингредиентов')
