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
        """Test updating a category"""
        url = reverse('category-detail', kwargs={'pk': self.category.pk})
        data = {'name': 'Updated Category', 'color': '#00FF00'}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, data['name'])

    def test_delete_category(self):
        """Test deleting a category"""
        url = reverse('category-detail', kwargs={'pk': self.category.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_access_any_category(self):
        """Test that users can access any public category"""
        other_category = CategoryFactory()
        url = reverse('category-detail', kwargs={'pk': other_category.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_any_category(self):
        """Test that any user can update any category"""
        other_category = CategoryFactory()
        url = reverse('category-detail', kwargs={'pk': other_category.pk})
        data = {'name': 'Updated Public Category', 'color': '#123456'}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        other_category.refresh_from_db()
        self.assertEqual(other_category.name, data['name'])
