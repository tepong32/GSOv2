from django import forms
from .models import Item


class ItemForm(forms.ModelForm):    
    class Meta:
    	model = Item
    	fields = ['date', 'obrNum', 'category', 'sub_category', 'brand', 'supplier', 'price_per_unit', 'qty', 'status', 'returned_date', 'notes']
    	widgets = {
    		# 'tag'
    		# 'category' : forms.Select(choices=categories, attrs={'class': 'form-control'})
    	}

    ### or you can use "exclude" if it fits your usage: ###
    # class Meta:
    #     model = YourModel
    #     exclude = ['field_to_exclude1', 'field_to_exclude2']

