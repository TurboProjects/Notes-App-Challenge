from rest_framework import serializers
from api.notes.models import Note, Category

class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for Category model
    """
    note_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'color', 'note_count')
        read_only_fields = ('id', 'note_count')

    def validate_name(self, value):
        user = self.context['request'].user
        if Category.objects.filter(user=user, name=value).exists():
            raise serializers.ValidationError("A category with this name already exists.")
        return value

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
        user = self.context['request'].user if 'request' in self.context else None

        if not Category.objects.visible_to(user).filter(id=value).exists():
            raise serializers.ValidationError("Invalid category ID")
        return value

    def create(self, validated_data):
        category_id = validated_data.pop('category_id')
        category = Category.objects.visible_to(self.context['request'].user).get(id=category_id)
        return Note.objects.create(
            category=category,
            **validated_data
        )

    def update(self, instance, validated_data):
        # Validate category_id if provided
        if 'category_id' in validated_data:
            category_id = validated_data.pop('category_id')
            try:
                user = self.context['request'].user if 'request' in self.context else None

                category = Category.objects.visible_to(user).get(id=category_id)
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
