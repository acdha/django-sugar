"""
Extensions for the Django template system
"""
from django import template
from django.core.serializers import serialize
from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

try:
    import simplejson as json
except ImportError:
    import json


register = template.Library()

class RenderInlineNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        source = self.nodelist.render(context)
        t = template.Template(source)
        return t.render(context)

@register.tag
def render_inline(parser, token):
    """
    Renders its contents to a string using the current context, allowing you
    to process template variables embedded in things like model content,
    django-flatblocks, etc.

    Usage:

    {%% render_inline %%}
    Foo

    Bar

    {{ something_with_embedded_django_template }}

    Baaz

    {%% end_render_inline %%}

    """

    nodelist = parser.parse(('end_render_inline',))

    parser.delete_first_token()

    return RenderInlineNode(nodelist)

class ContextManipulator(template.Node):
    """Add variables to the current template context

    Example:
        {%% set_context foo="bar" baaz=quux %%}
        {{ foo }} <- this will display "bar"
        {{ baaz }} <- the same as {{ quux }}

    """
    set_global = False

    def __init__(self, *args):
        if args[0] == "global":
            args = args[1:]
            self.set_global = True

        self.args = args

    def render(self, context):
        for arg in self.args:
            k, v = arg.split("=", 2)
            resolved_v = template.Variable(v).resolve(context)

            if not self.set_global:
                context[k] = resolved_v
            else:
                # Putting the crazy back in global:
                for d in context.dicts:
                    d[k] = resolved_v

        return ""

    @classmethod
    def set_context_tag(cls, parser, token):
        try:
            bits = token.split_contents()
        except ValueError:
            raise template.TemplateSyntaxError(
                _('set_context tag requires at least one arguments')
            )

        return ContextManipulator(bits[1], *bits[2:])

register.tag('set_context', ContextManipulator.set_context_tag)

@register.filter
def get_key(dict, key):
    """Trivial helper for the common case where you have a dictionary and want one value"""
    return dict.get(key, None)

@register.filter
def as_json(val):
    if isinstance(object, QuerySet):
        v = serialize('json', val)
    else:
        v = json.dumps(val)

    return mark_safe(v)
