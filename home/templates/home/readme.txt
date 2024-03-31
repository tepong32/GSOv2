Home folder will include static pages available for authed-users and site visitors.
About page, Ads, Affiliate links, Dev Portfolio, etc.

Pages:
	index.html			- most-likely, will just contain how the overall format of the django "extends" & "include" tags will be
	nav.html			- can be split into a separate nav for authed and un-authed users, depending on the site's purpose
	about.html			- self-explanatory
	contact.html		- not included here because I already placed socmed links on footer
	footer.html			- self-explanatory

	css & js pages 		- if you decide to separate these, you can have them "included" on your html pages thru {% include %} tags

