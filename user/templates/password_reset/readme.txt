Change the base html file which these pages 'extend' depending on how you setup your templating system.

Example:
	{% extends 'home_authed/base.html' %}	- normally, this will be just 'home/index.html'. In this case tho, separate folders were used for authed and unauthed users so, the folder was named 'home_authed' and then the base html file to extend was 'base/html'.
	(I really hope that's making sense. Well, you can do it! :D) 