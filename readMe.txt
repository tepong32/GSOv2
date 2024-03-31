gsheet reference
	sheet lang, wag buong workbook
google login
view-only page
edit-page (is_staff or custom permissions/group)



-------------------------------
This project aims to eliminate the hassle (and excuses) of broken-down, relic PCs.
Additionally, working with GSheets provides utilities for data extracting (same as excel) but with additional features like:
	- working collaborately, real-time
	- being able to tell "who-made-what" changes
	- being able to "restore" certain versions of the record in cases someone intentionally deletes it (sabotage)


Initially, this is just for the General Services Office but, perhaps, creating slots/pages for other departments and eventually making this the official, centralized database/website for the LGU can be looked-into. We'll need more developers for that, tho.

-------------------------------
##This project features:
	- A feature to address employees' lack of accountability for work done (or not done)
		Thru the use of a user login system where users are manually added (and given permissions to do stuffs) by the system admin, we can minimize (hopefully, eradicate) employees' finger-pointing culture. Un-authorized/anonymous users are given "view-only" mode for the file. 

		Data privacy concerns do not need to be addressed yet for the app will (temporarily) run on a server computer inside the GSO's Office. The same will be handled accordingly if the project is to "go online" (have its own web address).

	- Real-time View-and-Edit mode for users simultaneously accessing the files
		Taking advantage of this feature implemented by Google Sheets, users will not have to worry about the file being in read-only mode if it is opened and being worked-on by another user. Both (or all) of the users' changes made to the file will be saved accordingly. 

	- Version History
		Real-time View-and-Edit mode is a Pro and a Con at the same time. However, since it is expected that working on a specific file "collaboratively" will be seldomly needed, the "Con" part of is minimized. Also, this is where "version history" feature for Google Sheets comes in. The admin (handler of the account where the files are saved) will be able to see which changes were made and ulltimately decide whether to keep all the changes made by the user or "restore" the file to an earlier version anytime.




-------------------------------
##Overview:
	Files/Sheets will be displayed on <u>read-only</u> mode if the user is not signed-in to the app (default view) and on <u>view-and-edit mode</u> if the user is signed-in. This will required two separate Gdrive share-links from the files to be displayed.

