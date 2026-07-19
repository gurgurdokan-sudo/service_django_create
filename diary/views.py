from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views import generic

from .forms import EntryForm
from .models import Entry


class EntryListView(generic.ListView):
    model = Entry
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        keyword = self.request.GET.get('q', '').strip()
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) | Q(body__icontains=keyword)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['keyword'] = self.request.GET.get('q', '')
        return context


class EntryDetailView(generic.DetailView):
    model = Entry


class EntryCreateView(generic.CreateView):
    model = Entry
    form_class = EntryForm

    def form_valid(self, form):
        messages.success(self.request, '日報を作成しました。')
        return super().form_valid(form)


class EntryUpdateView(generic.UpdateView):
    model = Entry
    form_class = EntryForm

    def form_valid(self, form):
        messages.success(self.request, '日報を更新しました。')
        return super().form_valid(form)


class EntryDeleteView(generic.DeleteView):
    model = Entry
    success_url = reverse_lazy('diary:list')

    def form_valid(self, form):
        messages.success(self.request, '日報を削除しました。')
        return super().form_valid(form)
