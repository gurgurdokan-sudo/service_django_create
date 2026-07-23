from django.shortcuts import render, redirect

from dashboard.forms import officeSettigForm
from employees.permissions import delete_permission_required

import logging
logger = logging.getLogger(__name__)
@delete_permission_required
def office_setting(request):
    office = getattr(request.user, 'office', None)
    display_labels = {}
    if office:
        for field in office._meta.fields:
            if field.name.startswith('_'):
                continue
            label = field.verbose_name
            value = getattr(office, field.name)

            display_labels[label] = value if value is not None else "-"
    else:
        logger.error('事務所に紐づかないStaff')
        return redirect('dashboard:user_list')
    if request.method == 'POST':
        form = officeSettigForm(request.POST)
        if form.is_valid():
            office = form.save(commit=False)
            # office. = request.staff
            office.save()
            return redirect('dashboard:user_settig')
    else: form = officeSettigForm(instance=office)
    return render(request, 'dashboard/office_settig.html', {
        'display_labels': display_labels,
        'form': form
    })
