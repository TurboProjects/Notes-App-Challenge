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
        self.category = CategoryFactory()
        Note.objects.create(title="Test Note", category=self.category, user=self.user)
        self.url = reverse('category-list')

    def test_list_categories(self):
        """Test listing all public categories"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.category.id)
        self.assertEqual(response.data[0]['note_count'], 1)

    def test_create_category(self):
        """Test creating a category"""
        data = {'name': 'New Category', 'color': '#FF0000'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], data['name'])

    def test_update_category(self):
        """Test updating a category the user owns"""
        own_category = CategoryFactory(user=self.user)
        url = reverse('category-detail', kwargs={'pk': own_category.pk})
        data = {'name': 'Updated Category', 'color': '#00FF00'}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        own_category.refresh_from_db()
        self.assertEqual(own_category.name, data['name'])

    def test_delete_category(self):
        """Test deleting a category the user owns"""
        own_category = CategoryFactory(user=self.user)
        url = reverse('category-detail', kwargs={'pk': own_category.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_access_any_global_category(self):
        """Test that users can read any global category"""
        other_category = CategoryFactory()
        url = reverse('category-detail', kwargs={'pk': other_category.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cannot_update_global_category(self):
        """Test that global categories are read-only for regular users"""
        global_category = CategoryFactory()
        url = reverse('category-detail', kwargs={'pk': global_category.pk})
        data = {'name': 'Hijacked Category', 'color': '#123456'}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_delete_global_category(self):
        """Test that global categories cannot be deleted by regular users"""
        global_category = CategoryFactory()
        url = reverse('category-detail', kwargs={'pk': global_category.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestUserScopedCategories(APITestCase):
    """
    Test suite for user-scoped category behavior
    """
    def setUp(self):
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.global_category = CategoryFactory()
        self.own_category = CategoryFactory(user=self.user)
        self.other_category = CategoryFactory(user=self.other_user)
        self.url = reverse('category-list')

    def test_list_excludes_other_users_categories(self):
        """Test that listing returns own and global categories only"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [c['id'] for c in response.data]
        self.assertIn(self.global_category.id, ids)
        self.assertIn(self.own_category.id, ids)
        self.assertNotIn(self.other_category.id, ids)

    def test_create_assigns_authenticated_user_as_owner(self):
        """Test that POST sets the request user as category owner"""
        response = self.client.post(self.url, {'name': 'Mine', 'color': '#FF0000'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        category = Category.objects.get(id=response.data['id'])
        self.assertEqual(category.user, self.user)

    def test_duplicate_name_for_same_user_rejected(self):
        """Test that a user cannot repeat one of their category names"""
        self.client.post(self.url, {'name': 'Drama', 'color': '#FF0000'})
        response = self.client.post(self.url, {'name': 'Drama', 'color': '#00FF00'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)

    def test_same_name_allowed_for_different_users(self):
        """Test that different users can own categories with the same name"""
        CategoryFactory(user=self.other_user, name='Drama')
        response = self.client.post(self.url, {'name': 'Drama', 'color': '#FF0000'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_blank_name_rejected(self):
        """Test that empty or whitespace names are rejected"""
        response = self.client.post(self.url, {'name': '   ', 'color': '#FF0000'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_access_other_users_category(self):
        """Test that another user's private category is not reachable"""
        url = reverse('category-detail', kwargs={'pk': self.other_category.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_note_cannot_use_other_users_category(self):
        """Test that a note cannot be assigned to another user's category"""
        note = Note.objects.create(
            title="Test Note", category=self.own_category, user=self.user
        )
        url = reverse('note-detail', kwargs={'pk': note.pk})
        response = self.client.patch(
            url, {'category_id': self.other_category.id}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_notes_filter_by_other_users_category_not_found(self):
        """Test that filtering notes by an inaccessible category returns 404"""
        response = self.client.get(
            reverse('note-list'), {'category_id': self.other_category.id}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
