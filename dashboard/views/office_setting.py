from django.db.models.fields import return_None
from django.http import request
from django.shortcuts import render, redirect

from dashboard.forms import officeSettigForm
from employees.permissions import delete_permission_required

@delete_permission_required
def office_settig(request):
    if request.method == 'POST':
        form = officeSettigForm(request.POST)
        if form.is_valid():
            office = form.save(commit=False)
            # office.user = request.user
            office.save()
            return redirect('dashboard:user_settig')
    else: form = officeSettigForm(instance=request.user)
    return render(request, 'dashboard/office_settig.html', {'form': form})
