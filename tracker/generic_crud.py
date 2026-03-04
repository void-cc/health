from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime

from .decorators import staff_only


def _parse_field_value(field_cfg, raw_value):
    """Parse a POST value according to the field's type configuration."""
    field_type = field_cfg.get('type', 'str')
    default = field_cfg.get('default')

    if field_type == 'float':
        return float(raw_value) if raw_value else default
    elif field_type == 'int':
        return int(raw_value) if raw_value else default
    elif field_type == 'bool':
        return raw_value == 'on'
    elif field_type == 'date':
        return datetime.strptime(raw_value, '%Y-%m-%d').date() if raw_value else default
    elif field_type == 'datetime':
        return datetime.strptime(raw_value, '%Y-%m-%dT%H:%M') if raw_value else default
    elif field_type == 'time':
        return raw_value if raw_value else default
    else:  # str
        if default is None:
            default = ''
        return raw_value if raw_value else default


def _resolve_extra_context(extra, request):
    """Resolve extra context that may be a dict or a callable(request)."""
    if extra is None:
        return {}
    if callable(extra):
        return extra(request)
    return dict(extra)


def make_crud_views(
    model_class,
    display_name,
    fields,
    list_url_name,
    add_url_name,
    edit_url_name,
    order_by='-date',
    extra_list_context=None,
    extra_form_context=None,
    list_template='generic_list.html',
    form_template='generic_form.html',
    require_staff=True,
):
    """
    Factory that generates list, add, edit, and delete views for a model.

    Returns a dict with keys 'list', 'add', 'edit', 'delete' containing
    the four view functions.  When *require_staff* is True (the default)
    each view is guarded by ``@staff_only`` so only staff users may access
    it.  When *require_staff* is False the views are guarded by
    ``@login_required`` instead, making them suitable for personal health
    data that every authenticated user should be able to access.
    """

    _guard = staff_only if require_staff else login_required

    delete_url_name = list_url_name.rsplit('_list', 1)[0] + '_delete'

    # Ensure every field dict has a 'label' derived from 'name' if not provided
    for f in fields:
        if 'label' not in f:
            f['label'] = f['name'].replace('_', ' ').title()
        f.setdefault('required', False)

    # -- list view --
    @_guard
    def list_view(request):
        entries = model_class.objects.all().order_by(order_by)
        context = {
            'entries': entries,
            'page_title': display_name,
            'add_url_name': add_url_name,
            'edit_url_name': edit_url_name,
            'delete_url_name': delete_url_name,
            'fields': fields,
        }
        context.update(_resolve_extra_context(extra_list_context, request))
        return render(request, list_template, context)

    has_date = any(f['name'] == 'date' for f in fields)

    # -- add view --
    @_guard
    def add_view(request):
        if request.method == 'POST':
            if has_date:
                date_str = request.POST.get('date')
                if not date_str:
                    messages.error(request, 'Please select a date.')
                    return redirect(add_url_name)

            try:
                kwargs = {}
                for f in fields:
                    name = f['name']
                    kwargs[name] = _parse_field_value(f, request.POST.get(name))

                model_class.objects.create(**kwargs)
                messages.success(request, f'{display_name} entry added!')
                return redirect(list_url_name)
            except Exception:
                messages.error(request, f'Error adding {display_name.lower()}. Please try again.')
                return redirect(add_url_name)

        context = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'editing': False,
            'page_title': display_name,
            'list_url_name': list_url_name,
            'fields': fields,
            'entry': None,
        }
        context.update(_resolve_extra_context(extra_form_context, request))
        return render(request, form_template, context)

    # -- edit view --
    @_guard
    def edit_view(request, pk):
        entry = get_object_or_404(model_class, id=pk)
        if request.method == 'POST':
            try:
                for f in fields:
                    name = f['name']
                    setattr(entry, name, _parse_field_value(f, request.POST.get(name)))
                entry.save()
                messages.success(request, f'{display_name} updated!')
                return redirect(list_url_name)
            except Exception:
                messages.error(request, f'Error updating {display_name.lower()}.')
                return redirect(edit_url_name, pk=pk)

        context = {
            'entry': entry,
            'editing': True,
            'page_title': display_name,
            'list_url_name': list_url_name,
            'fields': fields,
        }
        context.update(_resolve_extra_context(extra_form_context, request))
        return render(request, form_template, context)

    # -- delete view --
    @_guard
    def delete_view(request, pk):
        if request.method == 'POST':
            entry = get_object_or_404(model_class, id=pk)
            entry.delete()
            messages.success(request, f'{display_name} entry deleted!')
        return redirect(list_url_name)

    return {
        'list': list_view,
        'add': add_view,
        'edit': edit_view,
        'delete': delete_view,
    }
