import factory
from unittest.mock import patch
from faker import Faker

from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from api.users.models import User
from api.notes.models import Note, Category
from api.users.test.factories import UserFactory
from api.notes.test.factories import CategoryFactory

fake = Faker()


class TestCategoryViewSet(APITestCase):
    """
    Test suite for Category ViewSet
    """
    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        # The fixture category is owned by the authenticated user.
        self.category = CategoryFactory(category_owner_user=self.user)
        Note.objects.create(title="Test Note", category=self.category, user=self.user)
        self.url = reverse('category-list')

    def test_list_categories(self):
        """List returns the user's own categories plus global ones."""
        global_category = CategoryFactory()  # category_owner_user is None
        other_user_category = CategoryFactory(category_owner_user=UserFactory())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {c['id'] for c in response.data}
        self.assertIn(self.category.id, returned_ids)
        self.assertIn(global_category.id, returned_ids)
        # Another user's private category must not be visible.
        self.assertNotIn(other_user_category.id, returned_ids)

    def test_create_category_sets_owner(self):
        """Creating a category assigns the authenticated user as owner."""
        data = {'name': 'New Category', 'color': '#FF0000'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], data['name'])
        self.assertEqual(str(response.data['category_owner_user']), str(self.user.id))
        created = Category.objects.get(id=response.data['id'])
        self.assertEqual(str(created.category_owner_user_id), str(self.user.id))

    def test_update_own_category(self):
        """A user can update their own category."""
        url = reverse('category-detail', kwargs={'pk': self.category.pk})
        data = {'name': 'Updated Category', 'color': '#00FF00'}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, data['name'])

    def test_delete_own_category(self):
        """A user can delete their own category."""
        url = reverse('category-detail', kwargs={'pk': self.category.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_read_global_category(self):
        """Global categories are readable by any authenticated user."""
        global_category = CategoryFactory()
        url = reverse('category-detail', kwargs={'pk': global_category.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cannot_update_global_category(self):
        """Global categories are read-only and cannot be edited."""
        global_category = CategoryFactory()
        url = reverse('category-detail', kwargs={'pk': global_category.pk})
        data = {'name': 'Hijacked Global', 'color': '#123456'}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        global_category.refresh_from_db()
        self.assertNotEqual(global_category.name, data['name'])

    def test_cannot_delete_global_category(self):
        """Global categories cannot be deleted by regular users."""
        global_category = CategoryFactory()
        url = reverse('category-detail', kwargs={'pk': global_category.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_access_other_users_category(self):
        """Another user's private category is not accessible (404, out of scope)."""
        other_category = CategoryFactory(category_owner_user=UserFactory())
        url = reverse('category-detail', kwargs={'pk': other_category.pk})

        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)

        put_response = self.client.put(
            url, {'name': 'Nope', 'color': '#123456'}
        )
        self.assertEqual(put_response.status_code, status.HTTP_404_NOT_FOUND)
