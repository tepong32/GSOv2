from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class UserRegisterForm(UserCreationForm):
	'''
		these fields take arguments (required=true/false).
		by default, required=true
	'''
	# add fields to this form
	email = forms.EmailField() 

	class Meta:
		model = User 	# the mode that is going to be affected is the User model
		fields = ["username", "email", "password1", "password2", ]


# after adding these forms, add it to the views.py
class UserUpdateForm(forms.ModelForm):
	'''
		these fields take arguments (required=true/false).
		by default, required=true
	'''
	email = forms.EmailField()

	class Meta:
		model = User 	# the model that is going to be affected is the User model, 
		fields = ["email", "first_name", "middle_name", "last_name", "ext_name", "image"]	# "username" & "department" field should not be user-changeable


