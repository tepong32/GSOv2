from django.db import models
# from django.contrib.auth.models import User
from user.models import User



class Category(models.Model):
	name = models.CharField(max_length=50)

	class Meta:
		verbose_name_plural = "Categories"

	def __str__(self):
		return f"{self.name}".strip()

class SubCategory(models.Model):
	name = models.CharField(max_length=50)

	class Meta:
		verbose_name_plural = "Sub-Categories"

	def __str__(self):
		return f"{self.name}".strip()



class Item(models.Model):
	
	date = models.DateField(help_text="yyyy-mm-dd format", verbose_name='Purchase Date')
	obrNum = models.PositiveSmallIntegerField(verbose_name="OBR #")
	category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, verbose_name="Category") # blank=False
	sub_category = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, verbose_name="Sub-Category") # blank=False
	brand = models.CharField(max_length=100, verbose_name="Brand")
	supplier = models.CharField(max_length=100, verbose_name="Supplier")
	price_per_unit = models.DecimalField(max_digits=11, decimal_places=2, help_text="from 0 to 999,999,999.99",verbose_name="Price per Unit")
	qty = models.PositiveSmallIntegerField(default=1, verbose_name="Qty")

	working = "Working"
	not_working = "Not Working"
	turned_over = "Turned Over to GSO"
	status_choices = [
		(working, "Working"),
		(not_working, "Not Working"),
		(turned_over, "Turned Over to GSO"),
	]
	status = models.CharField(blank=True, null=False, max_length=80, choices=status_choices, default=working, verbose_name="Status")
	returned_date = models.DateField(blank=True, null=True, help_text="Please do not forget to add the return-date here if the asset was surrendered to GSO", verbose_name="Return Date")
	notes = models.TextField(blank=True, verbose_name="Notes")
	
	### fields that are not so important to display but will be helpful in audit-checks and finger-pointing who to blame XD
	added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Added by") # sets the user who created the instance as the "added_by" attr
	added_on = models.DateTimeField(auto_now_add=True, null=True, verbose_name="added on") # automatically records the creation date of the instance
	modified_on = models.DateTimeField(auto_now=True, verbose_name="modified on") # when the entry gets modified, this will automatically change to the date&time the changes were saved

	def __str__(self):
		return f"{self.date} | {self.obrNum} | {self.brand} | {self.supplier}"












'''
date
obr
category (furniture, machine, accessory)
brand
price
qty
notes (s/n,)
status (working, not working, returned)


'''
