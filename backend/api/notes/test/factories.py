import factory
from api.notes.models import Category


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f'Category {n}')
    color = factory.Sequence(lambda n: f'#{"".join([str(n % 10) for _ in range(6)])}')
