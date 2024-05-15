from django.shortcuts import render
from django.contrib.auth.models import User
from django.core.paginator import Paginator

# for needing user to be logged-in first before accessing the page requested
from django.contrib.auth.decorators import login_required
from user.models import User, Department


@login_required
def home(request):

	# external links as variables
	# <!-- GSheet: add: "?widget=true&amp;headers=false" to share link -->
	# see home.html
	gso_inventory_link = "https://docs.google.com/spreadsheets/d/1aYRgmCa6urHjWlVTBWLQmyLYPXtnnM78/edit?usp=drive_link&ouid=101213569485981432969&rtpof=true&sd=true"
	departments = Department.objects.all()

	items = Item.objects.all().order_by("-date")
	paginator = Paginator(items, 10)  # Show 10 items per page
	page_number = request.GET.get('page')
	items_list = paginator.get_page(page_number)

	context = {
		'items': items_list,
		'gso_inventory_link': gso_inventory_link,
		'departments': departments,
	}

	# return render(request, 'home/index.html', context)
	return render(request, 'home/home.html', context)


def about(request):
	user = User
	context = {}
	return render(request, 'home/about.html', context)



##################################################################################################
from django.shortcuts import render, get_object_or_404
from .models import Item, Category, SubCategory
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (
	ListView,
	DetailView,
	CreateView,
	UpdateView,
	DeleteView,
	FormView,
	)
from .forms import ItemForm
from django.http import HttpResponseRedirect
from django.urls import reverse


import django_filters

from .models import Item

class ItemFilter(django_filters.FilterSet):
    class Meta:
        model = Item
        fields = ['category', 'sub_category', 'supplier', 'status', 'added_by']  # fields you want to filter on


class ItemListView(ListView):
    model = Item
    template_name = 'home/item_list.html'

    def get_queryset(self):
        queryset = super().get_queryset()
        self.filterset = ItemFilter(self.request.GET, queryset)
        return self.filterset.qs






class ItemDetailView(DetailView): # LoginRequiredMixin for authed users
	model = Item
	template_name = 'home/itemdetail.html'
	items = Item.objects.all()
	context = {
		'items': items,
	}


class ItemCreateView(LoginRequiredMixin, CreateView):		
	model = Item
	form_class = ItemForm
	template_name = 'home/itemcreateform.html'
	success_message = "Successfully posted!"
	success_url = '/'		# using this takes the user to a specific page after posting

	def form_valid(self, form):			# to automatically get the id of the current logged-in user as the author
		form.instance.added_by = self.request.user 	# set the author to the current logged-in user
		return super().form_valid(form)

class ItemUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
	model = Item 
	form_class = ItemForm	# blogPostForm was the one used in the tutorials
	template_name = 'home/itemupdateform.html'
	success_message = "Item updated"
	# success_url = '/blog'

	def form_valid(self, form):			
		form.instance.added_by = self.request.user 	#to automatically get the id of the current logged-in user as the author
		return super().form_valid(form)

	def test_func(self):
		item = self.get_object()

		if self.request.user == item.added_by:
			return True
		return False


class ItemDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):		
	model = Item
	template_name = 'home/itemconfirmdelete.html'
	success_url = '/'

	def form_valid(self, form):
		form.instance.added_by = self.request.user
		return super().form_valid(form)

	def test_func(self):
		item = self.get_object()

		if self.request.user == item.added_by:
			return True
		return False		



