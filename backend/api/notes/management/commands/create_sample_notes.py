from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.notes.models import Category, Note
from api.worker.celery import process_note_embeddings


# I'm sorry I need to create sample notes for test the AI assistant
# I have used cursor for this sample notes

SAMPLE_NOTES = [
    {
        "title": "Python Best Practices",
        "content": """Python is a versatile programming language known for its readability and simplicity.

Here are some best practices:
1. Use virtual environments to isolate project dependencies
2. Follow PEP 8 style guidelines for consistent code formatting
3. Write docstrings for functions and classes
4. Use type hints for better code documentation
5. Prefer list comprehensions over loops when appropriate
6. Use context managers (with statements) for resource management
7. Write unit tests for your code

Remember: Explicit is better than implicit, and simple is better than complex.""",
        "category": "School",
    },
    {
        "title": "Django REST Framework Tips",
        "content": """Django REST Framework (DRF) is a powerful toolkit for building Web APIs.

Key concepts:
- Serializers: Convert complex data types to Python native types
- ViewSets: Combine logic for multiple related views
- Routers: Automatically generate URL patterns
- Authentication: Token, Session, JWT options available
- Permissions: Control access to API endpoints
- Throttling: Rate limiting for API requests

Pro tip: Use ModelSerializer for quick CRUD operations and custom serializers for complex logic.""",
        "category": "School",
    },
    {
        "title": "Weekly Grocery List",
        "content": """Shopping list for the week:

Fruits:
- Apples (6)
- Bananas (bunch)
- Oranges (4)
- Strawberries (1 box)

Vegetables:
- Broccoli (2 heads)
- Carrots (1 bag)
- Spinach (1 bag)
- Tomatoes (4)

Proteins:
- Chicken breast (2 lbs)
- Salmon (1 lb)
- Eggs (1 dozen)

Dairy:
- Milk (1 gallon)
- Greek yogurt (2 cups)
- Cheese (cheddar block)""",
        "category": "Personal",
    },
    {
        "title": "Ideas for Weekend",
        "content": """Things I want to do this weekend:

Saturday:
- Morning jog at the park
- Brunch with friends at the new cafe downtown
- Afternoon: read that book I've been putting off
- Evening: try cooking a new recipe (maybe Thai curry?)

Sunday:
- Sleep in!
- Video call with family
- Organize closet and donate old clothes
- Meal prep for the week
- Watch a movie (check what's new on streaming)

Note to self: Don't forget to water the plants!""",
        "category": "Personal",
    },
    {
        "title": "Machine Learning Concepts",
        "content": """Key ML concepts to remember:

Supervised Learning:
- Classification: Predict categories (spam/not spam)
- Regression: Predict continuous values (house prices)

Unsupervised Learning:
- Clustering: Group similar items (customer segments)
- Dimensionality reduction: PCA, t-SNE

Neural Networks:
- Input layer, hidden layers, output layer
- Activation functions: ReLU, Sigmoid, Softmax
- Backpropagation for training

Important metrics:
- Accuracy, Precision, Recall, F1-Score
- MSE, RMSE for regression
- Cross-validation for model evaluation""",
        "category": "School",
    },
    {
        "title": "Random Shower Thoughts",
        "content": """Some random thoughts:

- If you clean a vacuum cleaner, are you the vacuum cleaner?
- Why do we park in driveways but drive on parkways?
- The word "bed" actually looks like a bed
- Your future self is watching you through memories
- Every book is a remix of the dictionary
- Technically, we're all just brains piloting a bone mech with meat armor

Life questions:
- What would I do if I won the lottery?
- If I could have dinner with anyone, who would it be?
- What skill do I wish I had learned earlier?""",
        "category": "Random Thoughts",
    },
    {
        "title": "Fitness Goals 2026",
        "content": """My fitness goals for this year:

Strength:
- Bench press: reach 185 lbs
- Squat: reach 225 lbs
- Deadlift: reach 275 lbs

Cardio:
- Run a 5K under 25 minutes
- Complete a 10K race
- Try swimming once a week

Habits:
- Go to gym 4x per week
- Drink 8 glasses of water daily
- Sleep at least 7 hours
- Reduce sugar intake

Monthly check-ins:
- Take progress photos
- Record weight and measurements
- Adjust goals as needed""",
        "category": "Personal",
    },
]


class Command(BaseCommand):
    help = "Creates sample notes for testing"

    def handle(self, *args, **kwargs):
        User = get_user_model()

        try:
            user = User.objects.get(email="admin@example.com")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("Admin user not found. Run create_init_objects first."))
            return

        deleted_count, _ = Note.objects.filter(user=user).delete()
        self.stdout.write(self.style.WARNING(f"Deleted {deleted_count} existing notes."))

        categories = {c.name: c for c in Category.objects.all()}
        if not categories:
            self.stdout.write(self.style.ERROR("No categories found. Run create_init_objects first."))
            return

        created_count = 0
        for note_data in SAMPLE_NOTES:
            category = categories.get(note_data["category"])
            if not category:
                self.stdout.write(self.style.WARNING(f"Category '{note_data['category']}' not found, skipping."))
                continue

            note = Note.objects.create(
                user=user,
                title=note_data["title"],
                content=note_data["content"],
                category=category,
            )
            created_count += 1
            process_note_embeddings.delay(note.id)
            self.stdout.write(self.style.SUCCESS(f"Created note: {note.title}"))

        self.stdout.write(self.style.SUCCESS(f"\nCreated {created_count} notes."))
