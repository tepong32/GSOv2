from django import template

register = template.Library()

@register.filter
def model_fields(model_instance):
    return model_instance._meta.fields

@register.filter
def get_attr(obj, attr):
    return getattr(obj, attr)



# will be using this one instead of the other two above
@register.filter
def model_dict(instance):
    return [(field.name, getattr(instance, field.name)) for field in instance._meta.fields]