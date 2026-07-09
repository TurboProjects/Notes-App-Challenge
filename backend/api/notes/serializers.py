from rest_framework import serializers
from django.db.models import Q
from api.notes.models import Note, Category


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for Category model
    """
    note_count = serializers.SerializerMethodField()
    # Read-only so the frontend can tell global (null) from personal categories.
    # Ownership is assigned by the view, never by the client.
    category_owner_user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'name', 'color', 'note_count', 'category_owner_user')
        read_only_fields = ('id', 'note_count', 'category_owner_user')

    def get_note_count(self, obj):
        user = self.context['request'].user if 'request' in self.context else None
        if user is None:
            return 0
        return obj.notes.filter(user=user).count()


class NoteSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = Note
        fields = (
            'id', 'title', 'content', 'category', 'category_id',
            'created_at', 'updated_at', 'user_id'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'user_id')

    def validate_category_id(self, value):
        # Only allow attaching the user's own categories or global ones
        # (category_owner_user is null). Prevents referencing another user's
        # private category by id.
        request = self.context.get('request')
        user = request.user if request else None
        category_qs = Category.objects.filter(
            Q(category_owner_user=user) | Q(category_owner_user__isnull=True)
        )
        if not category_qs.filter(id=value).exists():
            raise serializers.ValidationError("Invalid category ID")
        return value

    def create(self, validated_data):
        category_id = validated_data.pop('category_id')
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            raise serializers.ValidationError({
                "category_id": "Invalid category ID"
            })
        return Note.objects.create(
            category=category,
            **validated_data
        )

    def update(self, instance, validated_data):
        # Validate category_id if provided
        if 'category_id' in validated_data:
            category_id = validated_data.pop('category_id')
            try:
                category = Category.objects.get(id=category_id)
                instance.category = category
            except Category.DoesNotExist:
                raise serializers.ValidationError({
                    "category_id": "Invalid category ID"
                })
        
        # Update other fields
        instance.title = validated_data.get('title', instance.title)
        instance.content = validated_data.get('content', instance.content)
        instance.save()
        return instance
