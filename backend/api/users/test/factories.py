import uuid

import factory


class UserFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = 'users.User'
        django_get_or_create = ('username',)

    # LazyFunction (not Faker('uuid4')) so the pk is a real UUID, matching DB-loaded values
    id = factory.LazyFunction(uuid.uuid4)
    username = factory.Sequence(lambda n: f'testuser{n}')
    password = factory.Faker(
        'password',
        length=10,
        special_chars=True,
        digits=True,
        upper_case=True,
        lower_case=True
    )
    email = factory.Faker('email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    is_staff = False
    is_superuser = False
