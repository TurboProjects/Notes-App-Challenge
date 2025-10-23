import factory
from unittest.mock import patch
from faker import Faker

from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from api.users.models import User
from .factories import UserFactory

fake = Faker()


class TestUserListTestCase(APITestCase):
    """
    Tests /users list operations.
    """

    def setUp(self):
        self.url = reverse('user-list')
        self.user_data = {
            'first_name': fake.first_name(),
            'last_name': fake.last_name(),
            'email': fake.email(),
            'password': fake.password(),
        }

    def test_post_request_with_no_data_fails(self):
        """"
        Test that a POST request with no data fails.
        """
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_request_with_valid_data_succeeds(self):
        """
        Test that a POST request with valid data succeeds.
        """
        response = self.client.post(
            self.url, self.user_data,
            HTTP_ORIGIN='http://new.example.com'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(pk=response.data.get('id'))
        self.assertEqual(user.email, self.user_data.get('email'))
        self.assertEqual(user.first_name, self.user_data.get('first_name'))
        self.assertEqual(user.last_name, self.user_data.get('last_name'))


class TestUserDetailTestCase(APITestCase):
    """
    Tests /users detail operations.
    """

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse('user-detail', kwargs={'pk': self.user.pk})
        self.client.force_authenticate(user=self.user)

    def test_get_request_returns_a_given_user(self):
        """
        Test that a GET request returns a given user.
        """
        response = self.client.get(
            self.url, HTTP_ORIGIN='http://new.example.com'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_put_request_updates_a_user(self):
        """
        Test that a PUT request updates a user.
        """
        new_first_name = fake.first_name()
        payload = {'first_name': new_first_name}
        response = self.client.put(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that the user was updated
        user = User.objects.get(pk=self.user.id)
        self.assertEqual(user.first_name, new_first_name)


class CurrentUserViewTest(APITestCase):
    """
    Tests for the /users/me endpoint.
    """

    def test_get_current_user(self):
        """
        Test that a GET request to the /users/me/ endpoint returns the 
        currently authenticated user.
        """
        user = UserFactory()
        self.client.force_authenticate(user=user)
        url = reverse('user-me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], user.email)


class RegistrationViewTest(APITestCase):
    """
    Test suite for registration endpoint
    """
    def setUp(self):
        self.url = reverse('register')
        self.valid_payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }

    def test_valid_registration(self):
        """Test registration with valid data"""
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=self.valid_payload['email']).exists())
        self.assertIn('user', response.data)
        self.assertIn('message', response.data)

    def test_invalid_email_format(self):
        """Test registration with invalid email format"""
        payload = self.valid_payload.copy()
        payload['email'] = 'invalid-email'
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['errors'])

    def test_duplicate_email(self):
        """Test registration with existing email"""
        UserFactory(email=self.valid_payload['email'])
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['errors'])

    def test_missing_required_fields(self):
        """Test registration with missing fields"""
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['errors'])
        self.assertIn('password', response.data['errors'])
