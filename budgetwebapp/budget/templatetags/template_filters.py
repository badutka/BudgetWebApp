from django.template.defaulttags import register

# Custom template filter to get data from a dictionary using key in template

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)