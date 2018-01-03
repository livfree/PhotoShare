# PhotoShare
Database system for a web based photo social sharing application. 

To run:
Make sure everything in the requirements.txt file is downloaded to your local machine with the correct version.
Begin sql server, and start up sql: 
mysql -u root -h 127.0.0.1 -p
The database name is photoshare, and the password for the database is "giggaman123". 
Then run: python app.py, and open up http://127.0.0.1:5000/ in your web browser to use the app. 

The system manages the following information:

Users: each user is identified by a unique user id and has the following attributes: first name, last name, email, date of birth, hometown, gender, and password. A user can have a number of Albums.

Friends: each user can have any number of friends. 

Albums: each album is identified by a unique album id and has the following attributes: name, owner (user) id, and date of creation. The 'data' field contains the actual binary representation of the uploaded image file. Each album can contain a number of photos. 

Photos: each photo is identified by a unique photo id and must belong to an album. Each photo has the following attributes: caption and data. Each photo can only be stored in one album and is associated with zero, one, or more tags. 

Tags: each tag is described by a single word. Many photos can be tagged with the same tag.

Comments: each comment is identified by a unique comment id and has the following attributes: text (i.e., the actual comment), the comment's owner (a user) and the date the comment was left.

Likes: each user can like a photo, and users can see how many likes are on a photo. 

Files in this repository:

app.py connects to the databse and the the html pages and runs the app capabilities.

schema.sql contains the sql schema(table organization) in the photoshare database.

templates contains all of the html pages used in the web application.

requirements.txt contain all of the programs/processes needed to run this application.

static contains the css file for the photoshare web application. 
