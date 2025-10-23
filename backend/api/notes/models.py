from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

from api.notes.validators import validate_hex_color


class Category(models.Model):
    """
    Category model for organizing notes.
    """
    name = models.CharField(max_length=100)
    color = models.CharField(
        max_length=7,
        validators=[validate_hex_color]
    )

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return f"{self.name}"

    def clean(self):
        """
        Ensure name is not empty or just whitespace
        """
        if not self.name or not self.name.strip():
            raise ValidationError({'name': 'Name cannot be empty or whitespace'})
        self.name = self.name.strip()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def note_count(self):
        """
        Count the number of notes for the category
        """
        return self.notes.count()


class Note(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notes'
    )
    title = models.CharField(max_length=200, default="Untitled Note")
    content = models.TextField(blank=True, default="")
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.email} - {self.title}"

