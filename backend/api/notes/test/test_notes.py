from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from api.users.test.factories import UserFactory
from api.notes.test.factories import CategoryFactory
from api.notes.models import Note

class NoteAPITests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.category = CategoryFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('note-list')

    def test_create_note_success(self):
        """Test creating a note with valid data"""
        data = {'category_id': self.category.id}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Note.objects.count(), 1)
        self.assertEqual(response.data['category']['id'], self.category.id)

    def test_create_note_invalid_category(self):
        """Test creating note with invalid category"""
        data = {'category_id': 99999}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Note.objects.count(), 0)

    def test_create_note_unauthenticated(self):
        """Test creating note without authentication"""
        self.client.force_authenticate(user=None)
        data = {'category_id': self.category.id}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Note.objects.count(), 0)


class NotePatchTests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.category = CategoryFactory()
        self.note = Note.objects.create(
            user=self.user,
            category=self.category,
            title="Test Note",
            content="Test Content"
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('note-detail', kwargs={'pk': self.note.id})

    def test_patch_note_success(self):
        """Test updating a note with valid data"""
        new_category = CategoryFactory()
        data = {
            'title': 'Updated Title',
            'content': 'Updated Content',
            'category_id': new_category.id
        }
        response = self.client.patch(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, data['title'])
        self.assertEqual(self.note.content, data['content'])
        self.assertEqual(self.note.category.id, new_category.id)

    def test_patch_note_invalid_category(self):
        """Test updating note with invalid category"""
        data = {'category_id': 99999}
        response = self.client.patch(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category_id', response.data)

    def test_patch_other_user_note(self):
        """Test updating another user's note"""
        other_user = UserFactory()
        other_note = Note.objects.create(
            user=other_user,
            category=self.category,
            title="Other Note"
        )
        url = reverse('note-detail', kwargs={'pk': other_note.id})
        response = self.client.patch(url, {'title': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_note_unauthenticated(self):
        """Test updating note without authentication"""
        self.client.force_authenticate(user=None)
        data = {'title': 'Updated Title'}
        response = self.client.patch(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class NoteCategoryFilterTests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.category = CategoryFactory()
        self.other_category = CategoryFactory()

        # Create notes for testing
        self.notes_in_category = []
        for i in range(3):
            note = Note.objects.create(
                user=self.user,
                category=self.category,
                title=f"Note {i} in category"
            )
            self.notes_in_category.append(note)

        # Create notes in different category
        self.notes_other_category = []
        for i in range(2):
            note = Note.objects.create(
                user=self.user,
                category=self.other_category,
                title=f"Note {i} other category"
            )
            self.notes_other_category.append(note)

        self.client.force_authenticate(user=self.user)
        self.url = reverse('note-list')

    def test_filter_by_valid_category(self):
        """Test filtering notes by valid category_id"""
        response = self.client.get(f"{self.url}?category_id={self.category.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)
        for note in response.data['results']:
            self.assertEqual(note['category']['id'], self.category.id)

    def test_filter_by_invalid_category(self):
        """Test filtering by non-existent category"""
        response = self.client.get(f"{self.url}?category_id=99999")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_category_filter(self):
        """Test endpoint without category filter returns all user's notes"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)  # All notes for user

    def test_pagination_with_category_filter(self):
        """Test pagination works with category filter"""
        for i in range(25):
            Note.objects.create(
                user=self.user,
                category=self.category,
                title=f"Pagination test note {i}"
            )

        response = self.client.get(f"{self.url}?category_id={self.category.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 20)  # Default page size
        self.assertIsNotNone(response.data['next'])
        self.assertIsNone(response.data['previous'])

        response = self.client.get(f"{self.url}?category_id={self.category.id}&page=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 8)  # Remaining items
        self.assertIsNone(response.data['next'])
        self.assertIsNotNone(response.data['previous'])
