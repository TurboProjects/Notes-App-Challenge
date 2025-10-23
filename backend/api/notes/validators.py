import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_hex_color(value):
    """
    Validates that the value is a valid HEX color code.
    Valid formats: #RGB or #RRGGBB
    """
    if not re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', value):
        raise ValidationError(
            _('%(value)s is not a valid HEX color code'),
            params={'value': value},
        )
