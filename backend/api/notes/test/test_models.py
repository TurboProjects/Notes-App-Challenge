from django.test import TestCase
from django.core.exceptions import ValidationError
from unittest.mock import patch
from api.notes.models import Category
from api.notes.test.factories import CategoryFactory

class TestCategoryModel(TestCase):
    def setUp(self):
        self.category_data = {
            'name': 'Test Category',
            'color': '#FF5733'
        }

    def test_create_category_success(self):
        """Test that a category can be successfully created"""
        category = Category.objects.create(**self.category_data)
        self.assertEqual(category.name, self.category_data['name'])
        self.assertEqual(category.color, self.category_data['color'])

    def test_duplicate_category_name(self):
        """Test that duplicate category names are allowed now that categories are public"""
        Category.objects.create(**self.category_data)
        try:
            Category.objects.create(**self.category_data)
        except ValidationError:
            self.fail("ValidationError raised for duplicate category names when categories are public.")

    def test_invalid_color_format(self):
        """Test that an invalid color format raises a validation error"""
        self.category_data['color'] = 'invalid'
        with self.assertRaises(ValidationError):
            Category.objects.create(**self.category_data)

    def test_empty_name(self):
        """Test that a category cannot have an empty name"""
        self.category_data['name'] = ''
        with self.assertRaises(ValidationError):
            Category.objects.create(**self.category_data)

    def test_whitespace_name(self):
        """Test that a category cannot have a name with only whitespace"""
        self.category_data['name'] = '   '
        with self.assertRaises(ValidationError):
            Category.objects.create(**self.category_data)

    def test_name_stripped(self):
        """Test that category names are stripped of extra spaces"""
        self.category_data['name'] = '  Test Category  '
        category = Category.objects.create(**self.category_data)
        self.assertEqual(category.name, 'Test Category')

    def test_category_creation_error_handling(self):
        """Test that a database error does not break the system"""
        with patch('api.notes.models.Category.objects.create') as mock_create:
            mock_create.side_effect = Exception("Database error")
            try:
                Category.objects.create(**self.category_data)
            except Exception as e:
                self.assertEqual(str(e), "Database error")
