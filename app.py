######################################
# author ben lawson <balawson@bu.edu> 
# Edited by: Baichuan Zhou (baichuan@bu.edu) and Craig Einstein <einstein@bu.edu>
######################################
# Some code adapted from 
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################
#Project authors: Javiar Titus and Olivia Liberti
#CS460
######################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import time
import flask.ext.login as flask_login

# for image uploading
# from werkzeug import secure_filename
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'still a secret'  # Change this!

# These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'giggaman123'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

# begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT EMAIL FROM USER")
users = cursor.fetchall()


def getUserList():
    cursor = conn.cursor()
    cursor.execute("SELECT EMAIL FROM USER")
    return cursor.fetchall()


class User(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(email):
    users = getUserList()
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    return user


@login_manager.request_loader
def request_loader(request):
    users = getUserList()
    email = request.form.get('email')
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    cursor = mysql.connect().cursor()
    cursor.execute("SELECT PASSWORD FROM USER WHERE EMAIL = '{0}'".format(email))
    data = cursor.fetchall()
    pwd = str(data[0][0])
    user.is_authenticated = request.form['password'] == pwd
    return user


'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method != 'POST':
        return render_template('login.html', message='Login')
    else:
        # The request method is POST (page is recieving data)
        email = flask.request.form['email']
        cursor = conn.cursor()
        # check if email is registered
        if cursor.execute("SELECT PASSWORD FROM USER WHERE EMAIL= '{0}'".format(email)):
            data = cursor.fetchall()
            pwd = str(data[0][0])
            if flask.request.form['password'] == pwd:
                user = User()
                user.id = email
                flask_login.login_user(user)  # okay login in user
                return flask.redirect(flask.url_for('protected'))  # protected is a function defined in this file

        # information did not match
        return render_template('login.html', message="Incorrect Username or Password, please try again")


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return render_template('homepage.html', message='Logged out', users=topTenUsers())


@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('unauth.html')


# you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
    return render_template('register.html', supress='True')


@app.route("/register", methods=['POST'])
def register_user():
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        lastname = request.form.get('lastname')
        firstname = request.form.get('firstname')
        date = request.form.get('dob')
        if request.form.get('hometown'):
           hometown = request.form.get('hometown')
        else:
           hometown = "Not Listed"
        if request.form.get('gender'):
           gender = request.form.get('gender')
        else:
           gender = "Not listed"
    except:
        print "couldn't find all tokens" #prints to shell, users will not see this(all print statements go to shell)
        return flask.redirect(flask.url_for('register'))
    cursor = conn.cursor()
    test = isEmailUnique(email)
    if test:
        print(cursor.execute("INSERT INTO USER (GENDER, EMAIL, PASSWORD, DOB, HOMETOWN, FNAME, LNAME) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(gender, email, password, date, hometown, firstname, lastname)))
        conn.commit()
        # log user in
        user = User()
        user.id = email
        flask_login.login_user(user)
        return render_template('homepage.html', name=firstname, message='Account Created!')
    else:
        print "User already exists with this email"
        return flask.redirect(flask.url_for('register'))


def getUsersPhotos(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT PID, CAPTION, DATA FROM PHOTO WHERE UID= '{0}'".format(uid))
    return cursor.fetchall()  # NOTE list of tuples, [(imgdata, pid), ...]


def getUserIdFromEmail(email):
    cursor = conn.cursor()
    cursor.execute("SELECT UID FROM USER WHERE EMAIL = '{0}'".format(email))
    return cursor.fetchone()[0]

def getUserFnameFromEmail(email):
    cursor = conn.cursor()
    cursor.execute("SELECT FNAME FROM USER WHERE EMAIL = '{0}'".format(email))
    return cursor.fetchone()[0]

def isEmailUnique(email):
    # use this to check if a email has already been registered
    cursor = conn.cursor()
    if cursor.execute("SELECT EMAIL FROM USER WHERE EMAIL = '{0}'".format(email)):
        # this means there are greater than zero entries with that email
        return False
    else:
        return True


# end login code

@app.route('/profile')
@flask_login.login_required
def protected():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    everything = []
    query = "SELECT P.DATA, P.PID, P.CAPTION, A.NAME FROM PHOTO P, ALBUM A WHERE P.AID = A.AID AND P.UID='{0}'".format(uid)
    cursor.execute(query)
    allPhotos = cursor.fetchall()
    for i in allPhotos:
        everything += [getCommentsTagsAndLikes(i)]
    return render_template('profile.html', photos=everything, name=flask_login.current_user.id)


# begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML 
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def checkAlbumExists(userId):
   cursor = conn.cursor()
   query = "SELECT NAME, DOC FROM ALBUM WHERE UID='{0}'".format(userId)
   cursor.execute(query)
   return cursor.fetchall()


def checkAlbumName(name):
   cursor = conn.cursor()
   query = "SELECT NAME FROM ALBUM WHERE NAME = '{0}'".format(name)
   if cursor.execute(query):
     return False
   else:
     return True

#check if the user is the album owner
def checkOwner(albumId, userId):
   cursor = conn.cursor()
   query = "SELECT * FROM ALBUM WHERE AID = '{0}' AND UID = '{1}'".format(albumId, userId)
   if cursor.execute(query):
     return True
   else:
     return False


@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
    userId = getUserIdFromEmail(flask_login.current_user.id)
    if (checkAlbumExists(userId)):
       if request.method == 'POST':
          imgfile = request.files['photo']
          caption = request.form.get('caption')
          aid = request.form.get('aid')
          #get the album name from the album id
          cursor = conn.cursor()
          query = "SELECT NAME FROM ALBUM WHERE AID = '{0}'".format(aid)
          cursor.execute(query)
          aName = cursor.fetchall()
          #print caption
          photo_data = base64.standard_b64encode(imgfile.read())
          if checkOwner(aid, userId) == True:
             #cursor.execute("INSERT INTO PHOTO (CAPTION, DATA, AID, UID) VALUES ('{0}', '{1}', '{2}', '{3}')".format(caption, photo_data, aid, userId))
             cursor.execute("INSERT INTO PHOTO (CAPTION, DATA, AID, UID) VALUES (%s, %s, %s, %s)", (caption, photo_data, aid, userId))
             conn.commit()
             #photoId 
             #print(getUsersPhotos(uid))
             return render_template('upload.html', message='Photo uploaded! Add another one?', AID=aid)
             # The method is GET so we return a  HTML form to upload the a photo.
          else:
             return render_template('upload.html', message="Cannot pick this album")
       else:
           return render_template('profile.html')
    else:
       return render_template('album.html', message= "You need to create an album before uploading")

# end photo uploading code

# friend code

@app.route('/friends', methods=['GET'])
@flask_login.login_required
def friend():
    userId = getUserIdFromEmail(flask_login.current_user.id)
    friendlist = getFriends(userId)
    return render_template('friends.html', friends=friendlist)

#friend search for registered user.
@app.route('/fsearch', methods=['GET', 'POST'])
@flask_login.login_required
def fsearch():
    cursor = conn.cursor()
    friendlist = findAllUsers()
    if(request.method != 'POST'):
        return render_template('fsearch.html', friend=friendlist,recfriends=recommend() )
    else:
        email = request.form.get('email')
        if getUserIdFromEmail(email) > 0:
            uid = getUserIdFromEmail(email)
            cursor.execute("SELECT FNAME, LNAME, GENDER, DOB, HOMETOWN FROM USER WHERE UID='{0}'".format(uid))
            user = cursor.fetchall()
            print(user)
            return render_template('fsearch.html', friends=findAllUsers(), search=user, name=getUserFnameFromEmail(flask_login.current_user.id), recfriends=recommend())
        else:
            return render_template('fsearch.html', friends=findAllUsers(), message="There are no users matching this email", name=getUserFnameFromEmail(flask_login.current_user.id), recfriends=recommend())


#add a friend
@app.route('/addfriend', methods=['POST'])
@flask_login.login_required
def addFriend():
    cursor = conn.cursor()
    userId = getUserIdFromEmail(flask_login.current_user.id)
    email = request.form.get('email')
    friendId = getUserIdFromEmail(email)
    if friendId > 0:
      query = "SELECT UID1, UID2 FROM FRIENDSHIP WHERE UID1 = '{0}' AND UID2 = '{1}'".format(userId, friendId)
      query2 = "SELECT UID1, UID2 FROM FRIENDSHIP WHERE UID1 = '{1}' AND UID2 = '{0}'".format(userId, friendId)
      if cursor.execute(query) or cursor.execute(query2):
         print("already friends")
         return render_template('friends.html', friends = getFriends(userId), message="You are already friends with this user")
      else:
        query2 = "INSERT INTO FRIENDSHIP(UID1, UID2) VALUES ('{0}', '{1}')".format(userId, friendId)
        cursor.execute(query2)
        conn.commit()
        print("friend has been added")
        return render_template('friends.html', friends=getFriends(userId), message="Friend has been added")
    else:
        return render_template('friends.html', friends=getFriends(userId), message="Choose a valid email")


def getFriends(userId):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM FRIENDSHIP F WHERE (UID1)='{0}' OR UID2='{1}'".format(userId, userId))
    friendships = cursor.fetchall()
    friends = []
    for i in friendships:
        if (i[0] != userId):
            friends += userName(i[0])
        else:
            friends += userName(i[1])
    return friends

#helper for get friends
def userName(userId):
    cursor = conn.cursor()
    query = "SELECT U.FNAME, U.LNAME, U.EMAIL, U.GENDER, U.HOMETOWN FROM USER U WHERE UID = '{0}'".format(userId)
    cursor.execute(query)
    return cursor.fetchall()


#find a user
def findUser(firstName='', lastName=''):
    cursor = conn.cursor()
    firstName = str(firstName)
    lastName = str(lastName)
    if (lastName != '') and (firstName == ''):
        query = "SELECT FNAME, LNAME, DOB, EMAIL, UID FROM USER WHERE LNAME = '{0}'".format(lastName)
        cursor.execute(query)
    elif (firstName != '') and (lastName == ''):
        query = "SELECT FNAME, LNAME, DOB, EMAIL, UID FROM USER WHERE FNAME = '{0}'".format(firstName)
        cursor.execute(query)
    else:
        query = "SELECT FNAME, LNAME, DOB, EMAIL, UID FROM USER WHERE FNAME = '{0}' AND LNAME = '{1}'".format(
            firstName, lastName)
        cursor.execute(query)
    return cursor.fetchall()


# end of friend code

# album code

#make an album
@app.route('/malbum', methods=['GET', 'POST'])
@flask_login.login_required
def createAlbum():
    if request.method != 'POST':
        return render_template('malbum.html')
    else:
        userId = getUserIdFromEmail(flask_login.current_user.id)
        name = request.form.get('album')
        if checkAlbumName(name) == True:
           cursor = conn.cursor()
           date = time.strftime("%Y-%m-%d")
           query = "INSERT INTO ALBUM(NAME, DOC, UID) VALUES('{0}', '{1}', '{2}')".format(name, date, userId)
           cursor.execute(query)
           conn.commit()
           aid = getAid(name, userId)
           return render_template('upload.html', AID=aid)
        else:
           return render_template('malbum.html', message="Pick a new album name")

@app.route('/ualbum', methods={'GET','POST'})
@flask_login.login_required
def updateAlbum():
    userId = getUserIdFromEmail(flask_login.current_user.id)
    if request.method != 'POST':
        return render_template('ualbum.html', albums = getAlbums(userId))
    else:
        album = request.form.get('album')
        aid = getAid(album, userId)
        return render_template('upload.html', AID=aid)

def getAlbums(userId):
    cursor = conn.cursor()
    query = "SELECT A.NAME, A.DOC FROM ALBUM A WHERE UID='{0}'".format(userId)
    cursor.execute(query)
    return cursor.fetchall()

#get album id from name and userid
def getAid(name, uid):
    cursor = conn.cursor()
    cursor.execute("SELECT A.AID FROM ALBUM A WHERE UID='{0}' AND NAME='{1}'".format(uid, name))
    return cursor.fetchall()[0][0]


def albumsHelper(uid):
   cursor = conn.cursor()
   query = "SELECT NAME, AID, DOC FROM ALBUM WHERE UID = '{0}'".format(uid)
   cursor.execute(query)
   return cursor.fetchall()

#displays all photos in an album and the comments, tags, and likes on each photo
@app.route('/albums', methods=['GET', 'POST'])
def albums():
    userId = getUserIdFromEmail(flask_login.current_user.id)
    cursor = conn.cursor()
    if request.method != 'POST':
        query = "SELECT AID, NAME, DOC FROM ALBUM WHERE UID = '{0}'".format(userId)
        cursor.execute(query)
        albumsFound = cursor.fetchall()
        return render_template("album.html", albums=albumsFound)
    else:
        pictures = []
        albumId = request.form.get('albumId')
        name = request.form["albumSearch"]
        query = "SELECT A.NAME, P.DATA, P.PID, P.CAPTION FROM ALBUM A, PHOTO P WHERE A.AID = P.AID AND A.AID =getAlbumPhotos '{0}' AND A.UID = '{1}'".format(albumId, userId)
        cursor.execute(query)
        albumPhotos = cursor.fetchall()
        for i in albumPhotos:
            pictures += [getCommentsTagsAndLikes(i)]
        return render_template("album.html", photos=pictures, albumName=name)

#gets the comments, tags and likes on a photo
def getCommentsTagsAndLikes(photo):
   tags = getTag2(photo[1])
   comments = getComments(photo[1])
   likes = getLikes(photo[1])
   userLikes = getUserLikes(photo[1])
   return [photo] + [tags] + [comments] + [likes] + [userLikes]

#deletes an album
@app.route("/dalbum", methods=['GET', 'POST'])
@flask_login.login_required
def deleteAlbum():
    userId = getUserIdFromEmail(flask_login.current_user.id)
    cursor = conn.cursor()
    if request.method != 'POST':
        return render_template("dalbum.html", albums = getAlbums(userId))
    else:
        album = request.form.get('album')
        aid = getAid(album, userId)
        cursor.execute("DELETE FROM ALBUM WHERE AID='{0}'".format(aid))
        conn.commit()
        return render_template("dalbum.html", message="Album is deleted")

#gets album photos
def getAlbumPhotos(albumId, userId):
    cursor = conn.cursor()
    query = "SELECT A.NAME, P.DATA, P.PID, P.CAPTION FROM ALBUM A, PHOTO P WHERE A.AID = P.AID AND A.AID = '{0}' AND A.UID = '{1}'".format(
        albumId, userId)
    cursor.execute(query)
    return cursor.fetchall()

#end of album code

#photo code
#photo search by tag
@app.route('/photoSearch', methods=['POST'])
def photoSearch():
    cursor = conn.cursor()
    tag = request.form.get('tag')
    results = [photosByTag(tag)]
    return render_template("tsearch.html", result=results)

#get all photos from all users for users and visitors
@app.route('/mpsearch', methods=['GET'])
def findAllPhotos():
     pictures = []
     cursor = conn.cursor()
     query = "SELECT P.DATA, P.PID, P.CAPTION, A.NAME FROM PHOTO P, ALBUM A WHERE P.AID = A.AID"
     cursor.execute(query)
     allPhotos = cursor.fetchall()
     for i in allPhotos:
        pictures += [getCommentsTagsAndLikes(i)]
     return render_template("mpsearch.html", photos = pictures, message="These are all of the photos", likes=youMayAlsoLike())

#get all photos for visitors
@app.route('/psearch', methods=['GET'])
def findAllPhotos2():
    cursor = conn.cursor()
    users = findAllUsers()
    result = []
    for i in users:
        photos = getUsersPhotos(i[0])
        for j in photos:
            result += [(j[2], j[0], i[1], i[2])]
    return render_template('psearch.html', photos=result, name=getUserFnameFromEmail(flask_login.current_user.id))

#helper function finds all users
def findAllUsers():
    cursor = conn.cursor()
    cursor.execute("SELECT U.UID, U.FNAME, U.LNAME, U.EMAIL, U.GENDER, U.HOMETOWN FROM USER U")
    users = cursor.fetchall()
    return users

#photo delete
@app.route('/dphotos', methods=['GET', 'POST'])
@flask_login.login_required
def photoDelete():
    cursor = conn.cursor()
    uid = getUserIdFromEmail(flask_login.current_user.id)
    if request.method != 'POST':
        return render_template('dphotos.html', photos=getUsersPhotos(uid))
    else:
        caption = request.form.get('caption')
        pid = request.form.get('pid')
        query = "DELETE FROM PHOTO WHERE PID='{0}' AND UID='{1}' AND CAPTION='{2}'".format(pid, uid, caption)
        cursor.execute(query)
        conn.commit()
        return render_template('dphotos.html', photos=getUsersPhotos(uid), message="Photo Deleted")


#get photos with a specific tag for general search
def photosByTag(tag):
    cursor = conn.cursor()
    cursor.execute("SELECT A.PID FROM ASSOCIATE A WHERE A.HASHTAG='{0}'".format(tag))
    pids = cursor.fetchall()
    pictures = []
    for i in pids:
        cursor.execute("SELECT P.DATA, P.PID, P.CAPTION FROM PHOTO P WHERE PID='{0}'".format(i[0]))
        pictures += [cursor.fetchall()]
    return pictures

# end of photo code

#comments section
#add a comment
@app.route('/acomment', methods=['POST'])
@flask_login.login_required
def comment():
    cursor = conn.cursor()
    userId = getUserIdFromEmail(flask_login.current_user.id)
    comment = request.form.get('comment')
    pictureId = request.form.get('pid')
    date = time.strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO COMMENT(CONTENT, DOC, UID, PID) VALUES('{0}', '{1}', '{2}', '{3}')".format(comment, date, userId, pictureId))
    conn.commit()
    return render_template('comments.html', message='Comment posted')

#go to comments page
@app.route('/comments', methods=['GET'])
@flask_login.login_required
def comments():
    return render_template('comments.html')

#get comments for each user photo
def getComments(pictureId):
    cursor = conn.cursor()
    cursor.execute("SELECT CONTENT, UID, DOC FROM COMMENT WHERE PID='{0}'".format(pictureId))
    return cursor.fetchall()

#search for comments
@app.route('/searchComment', methods=["POST"])
@flask_login.login_required
def searchComments():
    cursor = conn.cursor()
    comment = request.form.get("TXT")
    cursor.execute("SELECT DISTINCT C.UID, U.FNAME, U.LNAME, U.EMAIL, count.total FROM COMMENT C,(SELECT COUNT(C2.UID) AS total FROM COMMENT C2 ORDER BY total DESC ) AS count, USER U WHERE U.UID = C.UID AND C.CONTENT='{0}'".format(comment))
    results = cursor.fetchall()
    return render_template('comments.html', result=results)

#end comments section

#tag section
#add a tag
@app.route('/addTag', methods=['POST'])
@flask_login.login_required
def addTag():
    cursor = conn.cursor()
    uid = getUserIdFromEmail(flask_login.current_user.id)
    tag = request.form.get('tag')
    pid = request.form.get('pid')
    print(pictureOwner2(pid, uid))
    if pictureOwner2(pid, uid):
        #check if tags already exists, avoid duplicate errors
        query = "SELECT HASHTAG FROM TAG WHERE HASHTAG = '{0}'".format(tag)
        if cursor.execute(query):
            #check if tag is already on photo
            query = "SELECT HASHTAG, PID FROM ASSOCIATE WHERE HASHTAG = '{0}' AND PID = '{1}'".format(tag, pid)
            if cursor.execute(query):
              return render_template('mytsearch.html', message="Photo already has this tag!")
            else:
              query = "INSERT INTO ASSOCIATE(HASHTAG, PID) VALUES('{0}', '{1}')".format(tag, pid)
              cursor.execute(query)
              conn.commit()
              return render_template('mytsearch.html', message="Tag created")
        else:
            #check if tag is already on photo 
            query = "SELECT HASHTAG, PID FROM ASSOCIATE WHERE HASHTAG = '{0}' AND PID = '{1}'".format(tag,pid)
            if cursor.execute(query):
              return render_template('mytsearch.html', message="Photo already has this tag!")
            else:
              query = "INSERT INTO TAG(HASHTAG) VALUE('{0}')".format(tag)
              cursor.execute(query)
              conn.commit()
              query = "INSERT INTO ASSOCIATE(HASHTAG, PID) VALUES('{0}', '{1}')".format(tag, pid)
              cursor.execute(query)
              conn.commit()
              return render_template('mytsearch.html', message="Tag created")
    else:
        return render_template('mytsearch.html', message="You cannot tag someone else's photo or this photo does not exist")

#verify picture owner as helper function
def pictureOwner(pid, userId):
    cursor = conn.cursor()
    cursor.execute("SELECT UID FROM PHOTO WHERE PID='{0}'".format(pid))
    user = cursor.fetchall()[0]
    if(user[0] == userId):
       return True
    else:
       return False


def pictureOwner2(pid, userId):
    cursor = conn.cursor()
    query = "SELECT UID FROM PHOTO WHERE PID='{0}'"
    if cursor.execute(query.format(pid)):
      user = cursor.fetchall()[0]
      if(user[0] == userId):
         return True
      else:
         return False
    else:
         return False

#get user tags/search for them
@app.route('/mytsearch', methods=['GET', 'POST'])
@flask_login.login_required
def UserPicturesByTags():
    cursor = conn.cursor()
    userId = getUserIdFromEmail(flask_login.current_user.id)
    pictures = getUsersPhotos(userId)
    pictureids = []
    tagss = []
    results = []
    if request.method != 'POST':
        for i in pictures:
            pictureids += [i[0]]
        for j in pictureids:
            tagss += [getTag2(j)]
        return render_template('mytsearch.html', tags= tagss, name=userId)
    else:
        query = request.form.get('tag')
        pictures2 = photosByTag(query)
        for i in pictures:
            pictureids += [i[0]]
        for j in pictureids:
            tagss += [getTag2(j)]
        return render_template('mytsearch.html', photos=pictures2, tags=tagss, name=userId )

@app.route('/tsearch', methods=['GET', 'POST'])
def sitePicturesByTags():
    cursor = conn.cursor()
    tagss = []
    results = []
    if request.method != 'POST':
        cursor.execute("SELECT HASHTAG FROM TAG")
        tagss = cursor.fetchall()
        return render_template("tsearch.html", tags= tagss)
    else:
        cursor.execute("SELECT HASHTAG FROM TAG")
        tagss = cursor.fetchall()
        query = request.form.get('tag')
        cursor.execute("SELECT DISTINCT P.DATA, A.PID, P.CAPTION FROM ASSOCIATE A, PHOTO P WHERE A.PID=P.PID AND HASHTAG='{0}'".format(query))
        pictures = cursor.fetchall()
        return render_template('tsearch.html', tags=tagss, photos=pictures)

#helper function
def getTag(pictureId):
    cursor = conn.cursor()
    cursor.execute("SELECT HASHTAG FROM ASSOCIATE WHERE PID='{0}'".format(pictureId))
    return cursor.fetchall()[0][0]

def getTag2(pictureId):
    cursor = conn.cursor()
    cursor.execute("SELECT HASHTAG FROM ASSOCIATE WHERE PID='{0}'".format(pictureId))
    return cursor.fetchall()

#view tags for everyone
def ViewAllByTags():
    cursor = conn.cursor()
    cursor.execute("SELECT HASHTAG FROM TAG")
    tags = cursor.fetchall()
    results = []
    for i in tags:
        results += [photosByTag(i[0])]
    return render_template("tsearch.html", tags= tags, photos=results)

#view most popular tags
def popularTags():
    cursor = conn.cursor()
    results = []
    cursor.execute("SELECT DISTINCT A.HASHTAG, total.count FROM ASSOCIATE A, (SELECT COUNT(A.PID) as count FROM ASSOCIATE A ORDER BY count DESC LIMIT 15) as total ")
    results = cursor.fetchall()
    return results
#end tag section

#likes section

#count number of likes on a photo

@app.route("/likePhoto", methods=['POST', 'GET'])
@flask_login.login_required
def likePhoto():
   userId = getUserIdFromEmail(flask_login.current_user.id)
   cursor = conn.cursor()
   #query = "SELECT P.DATA, P.PID, P.CAPTION, A.NAME FROM PHOTO P, ALBUM A WHERE P.AID = A.AID"
   #cursor.execute(query)
   #allPhotos = cursor.fetchall()
   #pictures = []
   #for i in allPhotos():
   #   pictures += [getCommentsTagsAndLikes(i)]
   if request.method != 'POST':
     return render_template("like.html", name=getUserFnameFromEmail(flask_login.current_user.id))
   else:
     photoId = request.form.get("pid")
     if likeOkay(userId, photoId) == False:
       return render_template("like.html", name=getUserFnameFromEmail(flask_login.current_user.id), message="You already liked this photo")
     else:
        insertLike(userId, photoId)
        #cursor.execute(query)
        #allPhotos = cursor.fetchall()
        #pictures = []
        #for i in allPhotos():
        #  pictures += [getCommentsTagsAndLikes(i)]
        return render_template("like.html", name=getUserFnameFromEmail(flask_login.current_user.id), message="Photo has been liked")

#inserts like onto photo
def insertLike(userId, photoId):
   cursor = conn.cursor()
   date = time.strftime("%Y-%m-%d")
   query = "INSERT INTO LIKETABLE(UID, PID, DOC) VALUES('{0}', '{1}', '{2}')".format(userId, photoId, date)
   cursor.execute(query)
   conn.commit()

#makes sure photo hasn't already been liked
def likeOkay(userId, photoId):
   cursor = conn.cursor()
   query = "SELECT UID FROM LIKETABLE WHERE UID='{0}' AND PID='{1}'".format(userId, photoId)
   if cursor.execute(query):
     return False
   else:
     return True

#get all likes from a photo
def getLikes(pictureId):
   cursor = conn.cursor()
   query = "SELECT COUNT(L.PID) FROM LIKETABLE L  WHERE PID = '{0}'".format(pictureId)
   cursor.execute(query)
   return cursor.fetchall()

#get first and last name of users who have liked a photo
def getUserLikes(pictureId):
   cursor = conn.cursor()
   query = "SELECT U.FNAME, U.LNAME FROM USER U, LIKETABLE L WHERE U.UID = L.UID AND L.PID = '{0}'".format(pictureId)
   cursor.execute(query)
   return cursor.fetchall()

#end likes section

#friend recommendation section

def recommend():
   email = request.form.get('email')
   userId = getUserIdFromEmail(flask_login.current_user.id)
   print userId
   recommendedFriends = recHelp(userId)
   return recommendedFriends

def recHelp(userId):
   friends = getFriends2(userId)
   friendList = []
   for i in friends:
       friendList.append(getFriends2(i[0]))
   friendList = list(set(friendList))
   friendList2 ={}
   friendList2 = set(friendList[0])
   friends = set(friends)
   allFriends2 = []
   allFriends2 = list(friendList2 - friends)
   allFriends = []
   #print userName(userId)
   for i in friendList[0]:
     allFriends.append(userName(i))
   return allFriends

def getFriends2(userId):
    cursor = conn.cursor()
    query = "SELECT UID1 FROM FRIENDSHIP WHERE UID2='{0}'".format(userId)
    query2 = query + "  UNION SELECT UID2 FROM FRIENDSHIP WHERE UID1='{0}'".format(userId)
    cursor.execute(query2)
    return cursor.fetchall()

#end friend recommendation section
def commonTags(userId):
   cursor = conn.cursor()
   query = "SELECT A.HASHTAG, COUNT(A.PID) FROM ASSOCIATE A, PHOTO P WHERE P.PID = A.PID AND P.UID = '{0}' GROUP BY HASHTAG ORDER BY COUNT(A.PID) DESC LIMIT 5".format(userId)
   cursor.execute(query)
   return cursor.fetchall()

#you may also like section
def youMayAlsoLike():
   userId = getUserIdFromEmail(flask_login.current_user.id)
   commonT = commonTags(userId)
   list = []
   for i in commonT:
      list.append(getCommonTagPhoto(i[0], userId))
   if len(list) > 0:
     return list
   else:
     return "NONE"


def commonTags(userId):
   cursor = conn.cursor()
   query = "SELECT A.HASHTAG, COUNT(A.PID) FROM ASSOCIATE A, PHOTO P WHERE P.PID = A.PID AND P.UID = '{0}' GROUP BY HASHTAG ORDER BY COUNT(A.PID) DESC LIMIT 5".format(userId)
   cursor.execute(query)
   return cursor.fetchall()

#get the 5 most common tags
def getMostCommonTags():
   cursor = conn.cursor()
   query = "SELECT HASHTAG, Count(HASHTAG) FROM ASSOCIATE GROUP BY HASHTAG ORDER BY Count(HASHTAG) DESC LIMIT 5"
   cursor.execute(query)
   return cursor.fetchall()

#get the photos with the most common tags
def getCommonTagPhoto(tag, userId):
   cursor = conn.cursor()
   photoList = []
   result = []
   result2 = []
   if isinstance(tag, str):
       tags = tag.split()
   else:
       tags = tag
   for i in tags:
       query = "SELECT HASHTAG FROM TAG WHERE HASHTAG= '{0}'".format(i)
       cursor.execute(query)
       for j in cursor.fetchall():
           photoList.append(j[0])
   photoList = list(set([i for i in photoList if photoList.count(i) == len(tags)]))
   for i in photoList:
       query = "SELECT DATA, PID FROM PHOTO WHERE PID = '{0}'".format(i)
       cursor.execute(query)
       result.append(cursor.fetchall())
   for i in result:
       result2.append(i)
   return result2

#get photo using photo id
def idGetPhoto(photoId):
   cursor = conn.cursor()
   query = "SELECT A.NAME, P.DATA, P.PID, P.CAPTION, FROM ALBUM A, PHOTO P WHERE P.AID = A.AID AND P.PID = '{0}'".format(photoId)
   cursor.execute(query)
   return cursor.fetchall()

#end you may also like section

#find top 10 users
def topTenUsers():
   cursor = conn.cursor()
   pics = "SELECT UID, COUNT(PID) AS count FROM PHOTO GROUP BY UID"
   comment = "SELECT UID, COUNT(CID) AS count FROM COMMENT WHERE UID != -1 GROUP BY UID"
   sum = "SELECT U.FNAME, U.LNAME FROM USER U, (SELECT UID, SUM(count) as count FROM (" + pics + " UNION " + comment + " ) AS Temp WHERE UID != -1 GROUP BY UID) AS userCounts WHERE U.UID = userCounts.UID ORDER BY userCounts.count DESC LIMIT 10"
   cursor.execute(sum)
   return cursor.fetchall()

# default page
@app.route("/", methods=['GET'])
def hello():
    return render_template('homepage.html', ptags=popularTags(), topUs=topTenUsers())


if __name__ == "__main__":
    # this is invoked when in the shell  you run
    # $ python app.py
    app.run(port=5000, debug=True)
app.config['MYSQL_DATABASE_HOST'] = 'localhost'

