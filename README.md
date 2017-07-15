# COMS W4111 Course Project
### The PostgreSQL account: yld2104
### Members: Yingfan Linda Du, Jason Cheuk Nam Liang
### The URL of your web application: http://35.185.113.189:8111/

### Parts implemented:
#### User View of the Application -
* A user can register for a new account by providing his/her name, email, location and creating a valid username and password.
* On the homepage after logging in, users are greeted with recent posts in order of time by the user and their ExBuds. 
* On the sidebar of the homepage, current friends and pending friends displayed and the user can add/remove their friends. Groups that are managed by the user are also displayed with options to delete the group as well edit the group.
* A user can manage the groups they’re in charge of through the editGroup page that they access from their homepage. Note that users can only access the edit
* Group page of groups they are managing because the link is only displaye on homepage for groups they manage. On the editGroup page, users can edit description, tags, etc for the group as well as edit events and add events.
* A user can search for other users by entering their names or usernames, and can add them as ExBuds (friends). The other user will then see the user who added them as a “Pending Friend” so they can choose to add them back. This feature is more like a follow feature because you can friend someone and they may not friend you back. Users can also comment on friends’ posts. All Exbuds’ posts will be displayed on that user’s home page.
Users can access the create group forms through a button available on the groups page. Using this form, users can create new groups.

Side note: new tags can be added through either the editGroup form or createGroup form. Thus, if users want to tag the group something that doesn’t exist yet, they can first add the new tag. 

* Users can search for groups by group name or tags and can join the group by going to the group’s profile page. The web-app also offers recommendations for groups which the user’s ExBuds have joined. This recommendation is based off of number of friends in a group that you have not joined.
* On a group’s profile page, the user can see basic information about the group, all members in the group (where your friends will show up at the top of the list), the group’s upcoming events, and recent posts made in it. Here, you are also able to post and reply to posts in the group.
* A user can search events by event name, by the group that hosts the event, or by event description. The web-app also offers recommendations for upcoming events in which his/her ExBuds are participating. 
* On an event’s profile page, the user can see the sponsoring companies of the event, and by clicking the company name, the web-app will direct the user to the company’s main page. The event main page also includes an “interested” button and “going” button which allows the user to indicate his/her preference whether or not to attend the event (“interested” and “going” can also be cancelled) 
* Users can search for companies by their name, industry, or commodities. On a company’s profile page, the user can see the company’s retail locations, sponsored events and the company’s recent posts. The user can also write comments on a company’s post.
* Finally the user can click “logout” which directs the user to the login page.
#### Company View of the Application -
* Can make a company profile through link on company index page that takes the user to a form.
* Companies are greeted table of events they are sponsoring as well recent posts they have made. On the sidebar is a list of its retail locations as well as option for company to add more retail locations.
* Companies can search for an event by name or group through the events tab.
* Clicking an event name will take the company to the event’s profile page which looks similar to the user’s view. Instead of “interested/going,” companies have the option to sponsor the event or unsponsor.
* Clicking on any group’s name takes the company to the group’s profile page that looks similar to the user’s view. However, companies can only reply to posts in a group and cannot post directly to the group (to minimize ads presence in these groups).

#### General Notable Features -
* In both views, posts are diplayed with any comments made. Users/Companies can comment on any post.
* In both views, users can delete any post/comment that were created by them.

### Parts not implemented:
* Since we already implemented a login page for ordinary users , we did not implement the login page for companies (which is essentially the same as that for ordinary users) since we believe that this is not crucial to demonstrate our app’s interaction with our database. Instead for convenience we created a “Company View” tab for institutional users to access their own pages and write posts about events. 
* We did not implement the “like post” functionality since we already demonstrated multiple complex interactions between tables within our web-app and already have 15 relations, such that adding this functionality will over complicate our design. 

### Added feature:
* The comments feature (ability to comment on a post), as described above, was added to further enhance interactions between users posts and companies. To do this, we added an optional responseto attribute to the posts table.

### Two interesting pages and the reason why they are interesting:
* Edit Groups page: This is the page where the user can manage groups they are in charge of. Here, they can edit detail of the group such as assigning a new manager to the group, edit details of events as well as create new events for the group. This interesting because it lets the user interact with three different tables all on one page. The page consists of four key forms, one to add tags (interacts with the categories table), one to update the group information (affects both the tags and groups table), one to edit events hosted by the group being edited and creating new events (interacts with events table and locations table). The update forms pre-populate all the fields with whatever value they are currently. Thus, this makes it easy for the user to see and change what they want.
* Home Page - User: This is the page that greets the user when they log in. It’s interesting because it acts essentially as a summary of the whole application for the user. Here, users see groups they manage, friends and pending friends, recent posts their friends or they made, upcoming events they stated they were interested in or going to. Users are able to interact with the friends relationship table directly here, conveniently adding a pending friend of removing a friend on this page. They can also conveniently navigate to the profile page for any of the listed events or groups. This is also where users delete groups they are in charge of and access the page to manage the group. This page interacts with or provides views of 11 of our tables. Thus, this page brings together all the aspects of the application, interacting with almost all the tables in our application and has a little bit of everything.

Note: error handling implemented is that create forms simply redirect to the same form if some error occurred when trying to insert/update the table
