#!/usr/bin/env python2.7

"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver

To run locally:

    python server.py

Go to http://localhost:8111 in your browser.

A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool, exc
from flask import Flask, request, render_template, g, redirect, Response, url_for

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

DATABASEURI = "postgresql://yld2104:8938@104.196.135.151/proj1part2"

#
# Creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass

@app.route('/')
def index():
  return render_template("index.html")

@app.route('/demoIndex')
def demo():

  cursor = g.conn.execute("SELECT username FROM Users")
  names = []
  for result in cursor:
    names.append(result['username'])  # can also be accessed using result[0]
  cursor.close()
  
  context = dict(data = names)

  return render_template("demo.html", **context)

@app.route('/loginUser', methods=['POST'])
def loginUser():
  username = request.form['username']
  password = request.form['password']

  cursor = g.conn.execute("SELECT COUNT(*) FROM Users WHERE username=%s AND password=%s",username,password)
  status = cursor.fetchone()[0]
  url = '/'

  if status == 1:
    url = url_for("home",username=username)
  return redirect(url)

@app.route('/createUserForm')
def createUserForm():
  return render_template("createUser.html")

@app.route('/companyView')
def companyView():
  #All companies
  companies = []
  cursor = g.conn.execute("SELECT * FROM Companies")
  for res in cursor:
    companydata = dict(companyid=res['id'], name = res['name'], industry = res['industry'], commodities=res['commodities'])
    companies.append(companydata)
  cursor.close()
  context= dict(companies=companies) 
  return render_template("companyIndex.html",**context)

@app.route('/createCompanyForm')
def createCompanyForm():
  return render_template("createCompany.html")

@app.route('/<username>/home')
def home(username):
    #ManagedGroups
    cursor = g.conn.execute("SELECT * FROM Groups INNER JOIN Users ON Groups.managerid=Users.username WHERE Users.username=%s",username)
    managegroups = []
    for result in cursor:
        data = dict(name=result['name'], description=result['description'])
        managegroups.append(data)
    cursor.close()

    #Events (userid, name, host, status, start, end, description, friends)
    cursor = g.conn.execute("SELECT * FROM (UserParticipates INNER JOIN Events ON UserParticipates.hostid = Events.hostid AND UserParticipates.eventname = Events.name) AS E WHERE E.userid = %s AND E.status IN ('Going','Interested') AND E.endtime >= now() ORDER BY E.starttime ASC LIMIT 10",username)
    events = []
    for result in cursor:
        data = dict(userid=result['userid'],name=result['name'],host=result['hostid'],status=result['status'],start=result['starttime'],end=result['endtime'],description=result['description'])
        cursor2 = g.conn.execute("SELECT COUNT(*) AS friends FROM Events AS E INNER JOIN UserParticipates AS U ON E.hostid = U.hostid AND E.name = U.eventname WHERE U.userid IN (SELECT user2id FROM Friends WHERE user1id = %s) AND E.name = %s AND E.hostid = %s",username,data['name'],data['host'])
        numfriends = 0
        for r in cursor2:
            numfriends = r['friends']
        data['friends']=numfriends
        cursor2.close()
        events.append(data)
    cursor.close()
    
    #Posts (id, userid, text, group)
    cursor = g.conn.execute("SELECT * FROM (User_Posts INNER JOIN Posts ON User_Posts.postid = Posts.id INNER JOIN Users ON User_Posts.userid=Users.username) AS P WHERE (P.userid IN (SELECT user2id FROM Friends WHERE user1id = %s) OR P.userid = %s) AND P.responseto is null ORDER BY P.timestamp DESC LIMIT 10",username, username)
    messages = []
    for result in cursor:
        data = dict(id=result['postid'], firstname=result['firstname'], lastname=result['lastname'], userid=result['userid'],text=result['text'],group=result['groupid'])
        if username==result['userid']:
          data['owner'] = 1
        else:
          data['owner'] = 0 
        cursor2 = g.conn.execute("SELECT * FROM Posts AS P WHERE P.responseto = %s ORDER BY P.timestamp ASC",data['id'])
        comments = []
        for r in cursor2:
            r2 = g.conn.execute("SELECT * FROM Company_Posts INNER JOIN Companies ON Company_Posts.companyid=Companies.id WHERE postid=%s",r['id'])
            cp = r2.fetchone()
            r3 = g.conn.execute("SELECT * FROM User_Posts INNER JOIN Users ON User_Posts.userid=Users.username WHERE postid=%s",r['id'])
            up = r3.fetchone()
            if cp is not None:
              data2 = dict(id=r['id'], firstname=cp['name'], lastname="", userid=cp['companyid'], text=r['text'], group=None)
              data2['owner'] = 0
              comments.append(data2)
            if up is not None:
              data2 = dict(id=r['id'], firstname=up['firstname'], lastname=up['lastname'], userid=up['userid'], text=r['text'], group=up['groupid'])
              comments.append(data2)
              if username==up['userid']:
                data2['owner'] = 1
              else:
                data2['owner'] = 0 
            r2.close()
            r3.close()
        cursor2.close()
        post = dict(original=data, comments=comments)
        messages.append(post)
    cursor.close()

    #Friends (firstname, lastname, username)
    cursor = g.conn.execute("SELECT * FROM Friends INNER JOIN Users ON Friends.user2id = Users.username WHERE user1id = %s ORDER BY lastname, firstname",username)
    friends = []
    for result in cursor:
        data = dict(firstname=result['firstname'], lastname=result['lastname'],username=result['username'])
        friends.append(data)
    cursor.close()

    #Pending Friends (firstname, lastname, username)
    cursor = g.conn.execute("SELECT * FROM (Friends INNER JOIN Users ON Friends.user1id = Users.username) AS f WHERE f.user2id = %s AND NOT EXISTS(SELECT * FROM Friends WHERE user1id = %s AND user2id = f.user1id) ORDER BY f.created desc, f.lastname asc LIMIT 10",username,username)
    pfriends = []
    for result in cursor:
        data = dict(firstname=result['firstname'], lastname=result['lastname'],username=result['username'])
        pfriends.append(data)
    cursor.close()

    #Dictionary of variables
    context = dict(managegroups=managegroups, user=username, events=events, posts=messages, friends = friends, pfriends = pfriends)
    return render_template("home.html", **context)

@app.route('/<username>/users')
def users(username):
    users = []
    context = dict(user=username, users=users)
    return render_template("userSearch.html",**context)

@app.route('/<username>/groups')
def groups(username):
    #AllTags
    tags = []
    cursor2 = g.conn.execute('SELECT * FROM Categories')
    for t in cursor2:
      tags.append(dict(name=t['exercise_name'],description=t['description']))
    cursor2.close()

    #Your Groups(name, managerid, managerfirst, managerlast, description)
    groups = []
    cursor = g.conn.execute("SELECT * FROM (Groups INNER JOIN Members ON Groups.name = Members.groupid INNER JOIN Users ON Groups.managerid=Users.username) AS G WHERE G.userid = %s",username)
    for result in cursor:
        data = dict(name=result['name'], managerid=result['managerid'], managerfirst=result['firstname'], managerlast=result['lastname'], description=result['description'])
        groups.append(data)
    cursor.close()

    #Recommendations(cfriends, name, managerid, managerfirst, managerlast, description)
    recgroups = []
    cursor = g.conn.execute("SELECT G.name, COUNT(*) AS count FROM (Groups INNER JOIN Members ON Groups.name = Members.groupid) AS G WHERE G.userid IN (SELECT user2id FROM Friends WHERE user1id = %s) and NOT EXISTS (SELECT * FROM Members WHERE groupid = G.name AND userid = %s) GROUP BY G.name ORDER BY COUNT(*) DESC LIMIT 10",username,username)
    for r in cursor:
        cursor2 = g.conn.execute("SELECT * FROM (Groups INNER JOIN Users ON Groups.managerid=Users.username) AS G WHERE G.name = %s",r['name'])
        result = cursor2.fetchone();
        cursor2.close()
        data = dict(cfriends=r['count'], name=result['name'], managerid=result['managerid'], managerfirst=result['firstname'], managerlast=result['lastname'], description=result['description'])
        recgroups.append(data)
    cursor.close()

    #Dictionary of variables
    context = dict(tags=tags, user=username, groups=groups, recgroups = recgroups)

    return render_template("groups.html",**context)

@app.route('/<username>/events')
def events(username):

    #Events (userid, name, host, status, start, end, description, friends)
    cursor = g.conn.execute("SELECT * FROM (UserParticipates INNER JOIN Events ON UserParticipates.hostid = Events.hostid AND UserParticipates.eventname = Events.name) AS E WHERE E.userid = %s AND E.status IN ('Going','Interested') AND E.endtime >= now() ORDER BY E.starttime ASC LIMIT 10",username)
    events = []
    for result in cursor:
        data = dict(userid=result['userid'],name=result['name'],host=result['hostid'],status=result['status'],start=result['starttime'],end=result['endtime'],description=result['description'])
        cursor2 = g.conn.execute("SELECT COUNT(*) AS friends FROM Events AS E INNER JOIN UserParticipates AS U ON E.hostid = U.hostid AND E.name = U.eventname WHERE U.userid IN (SELECT user2id FROM Friends WHERE user1id = %s) AND E.name = %s AND E.hostid = %s",username,data['name'],data['host'])
        numfriends = 0
        for r in cursor2:
            numfriends = r['friends']
        data['friends']=numfriends
        cursor2.close()
        events.append(data)
    cursor.close()    

    #RecommendedEvents
    recevents = []
    cursor = g.conn.execute("SELECT E.name, E.hostid, COUNT(*) AS f FROM Events AS E INNER JOIN UserParticipates AS U ON E.hostid = U.hostid AND E.name = U.eventname WHERE U.userid IN (SELECT user2id FROM Friends WHERE user1id = %s) and NOT EXISTS (SELECT * FROM UserParticipates WHERE eventname = E.name AND hostid = E.hostid AND userid = %s) AND E.endtime > now() GROUP BY E.name, E.hostid ORDER BY COUNT(*) DESC LIMIT 10",username,username)
    for r in cursor:
        cursor2 = g.conn.execute("SELECT * FROM Events WHERE hostid=%s and name=%s",r['hostid'],r['name'])
        result=cursor2.fetchone()
        data = dict(friends=r['f'],name=result['name'],host=result['hostid'],start=result['starttime'],end=result['endtime'],description=result['description'])
        cursor2.close()
        recevents.append(data)
    cursor.close()

    context = dict(user=username,events=events,recevents=recevents)
    return render_template("events.html",**context)

@app.route('/<int:companyid>/eventsC')
def eventsC(companyid):

    events = []

    context = dict(companyid=companyid,events=events)
    return render_template("eventsSearchC.html",**context)

@app.route('/<username>/companies')
def companies(username):
    companies = []
    #All Companies
    cursor = g.conn.execute("SELECT * FROM Companies")
    for res in cursor:
      companydata = dict(companyid=res['id'], name = res['name'], industry = res['industry'], commodities=res['commodities'])
      companies.append(companydata)
    cursor.close()
    context= dict(user=username,companies=companies)
    return render_template("companySearch.html",**context)


@app.route('/<username>/userprofile/<pusername>')
def userprofile(username, pusername):

    #UserInfo
    cursor = g.conn.execute("SELECT * FROM Users WHERE username = %s",pusername)
    result = cursor.fetchone()
    userdata = dict(firstname=result['firstname'], lastname=result['lastname'], username=result['username'])
    cursor.close()

    #MutualFriends
    mutualfriends = []
    cursor = g.conn.execute("SELECT * FROM Friends f1 INNER JOIN Users ON f1.user2id = Users.username WHERE user1id = %s AND user2id IN (SELECT user1id FROM Friends f2 WHERE f2.user2id = %s)",username, pusername)
    for result in cursor:
      d = dict(firstname=result['firstname'], lastname=result['lastname'], username=result['username'])
      mutualfriends.append(d)
    cursor.close()

    #Friendship
    cursor = g.conn.execute("SELECT COUNT(*) FROM Friends WHERE user1id=%s and user2id=%s",username,pusername)
    status = cursor.fetchone()[0]
    cursor.close()

    #Posts (id, userid, text, group)
    cursor = g.conn.execute("SELECT * FROM (User_Posts INNER JOIN Posts ON User_Posts.postid = Posts.id INNER JOIN Users ON User_Posts.userid=Users.username) AS P WHERE P.userid = %s AND P.responseto is null ORDER BY P.timestamp DESC LIMIT 10",pusername)
    messages = []
    for result in cursor:
        data = dict(id=result['postid'], firstname=result['firstname'], lastname=result['lastname'], userid=result['userid'],text=result['text'],group=result['groupid'])
        data['owner'] = 0 
        cursor2 = g.conn.execute("SELECT * FROM Posts AS P WHERE P.responseto = %s ORDER BY P.timestamp ASC",data['id'])
        comments = []
        for r in cursor2:
            r2 = g.conn.execute("SELECT * FROM Company_Posts INNER JOIN Companies ON Company_Posts.companyid=Companies.id WHERE postid=%s",r['id'])
            cp = r2.fetchone()
            r3 = g.conn.execute("SELECT * FROM User_Posts INNER JOIN Users ON User_Posts.userid=Users.username WHERE postid=%s",r['id'])
            up = r3.fetchone()
            if cp is not None:
              data2 = dict(id=r['id'], firstname=cp['name'], lastname="", userid=cp['companyid'], text=r['text'], group=None)
              data2['owner'] = 0
              comments.append(data2)
            if up is not None:
              data2 = dict(id=r['id'], firstname=up['firstname'], lastname=up['lastname'], userid=up['userid'], text=r['text'], group=up['groupid'])
              comments.append(data2)
              if username==up['userid']:
                data2['owner'] = 1
              else:
                data2['owner'] = 0 
            r2.close()
            r3.close()
        cursor2.close()
        post = dict(original=data, comments=comments)
        messages.append(post)
    cursor.close()

    context = dict(posts = messages, data=userdata, user=username, mutualfriends=mutualfriends, status=status)
    return render_template("userprofile.html",**context)

@app.route('/<username>/eventprofile/<eventname>/<hostid>')
def eventprofile(username, eventname, hostid):

    #Attendance Stats
    cursor = g.conn.execute("SELECT COUNT(*) FROM UserParticipates WHERE eventname = %s AND hostid = %s AND status = 'Going'",eventname,hostid)
    going = cursor.fetchone()[0]
    cursor.close()
    cursor = g.conn.execute("SELECT COUNT(*) FROM UserParticipates WHERE eventname = %s AND hostid = %s AND status = 'Interested'",eventname,hostid)
    interested = cursor.fetchone()[0]
    cursor.close()

    cursor = g.conn.execute("SELECT * FROM UserParticipates WHERE eventname = %s and hostid=%s and userid = %s", eventname, hostid, username)
    r = cursor.fetchone()
    status = None
    if r is None:
      status = "None"
    else:
      status = r['status']
    cursor.close()

    #All Sponsors
    cursor = g.conn.execute("SELECT * FROM Sponsors INNER JOIN Companies ON Sponsors.companyid=Companies.id WHERE hostid=%s and eventname=%s",hostid,eventname)
    sponsors = []
    for result in cursor:
      s = dict(name=result['name'],id=result['companyid'])
      sponsors.append(s)
    cursor.close()

    #EventInfo
    cursor = g.conn.execute("SELECT * FROM Events INNER JOIN Locations ON Events.locationid=Locations.id WHERE hostid=%s and name=%s",hostid,eventname)
    result = cursor.fetchone()
    eventdata = dict(name=result['name'],hostid=result['hostid'],start=result['starttime'],end=result['endtime'],description=result['description'], locationid=result['locationid'], street=result['street'], city=result['city'],state=result['state'],zipcode=result['zipcode'])
    
    #cursor2 = g.conn.execute("SELECT COUNT(*) AS friends FROM Events AS E INNER JOIN UserParticipates AS U ON E.hostid = U.hostid AND E.name = U.eventname WHERE U.userid IN (SELECT user2id FROM Friends WHERE user1id = %s) AND E.name = %s AND E.hostid = %s",username,data['name'],data['host'])
    cursor.close()

    context = dict(user=username, sponsors=sponsors, going=going, interested=interested, status=status, data=eventdata)

    return render_template("eventprofile.html",**context)

@app.route('/<int:companyid>/eventprofileC/<eventname>/<hostid>')
def eventprofileC(companyid, eventname, hostid):

    #Attendance Stats
    cursor = g.conn.execute("SELECT COUNT(*) FROM UserParticipates WHERE eventname = %s AND hostid = %s AND status = 'Going'",eventname,hostid)
    going = cursor.fetchone()[0]
    cursor.close()
    cursor = g.conn.execute("SELECT COUNT(*) FROM UserParticipates WHERE eventname = %s AND hostid = %s AND status = 'Interested'",eventname,hostid)
    interested = cursor.fetchone()[0]
    cursor.close()

    #Sponsorship
    cursor = g.conn.execute("SELECT COUNT(*) FROM Sponsors WHERE companyid=%s AND eventname=%s AND hostid=%s",companyid,eventname,hostid)
    status = cursor.fetchone()[0]
    cursor.close()

    #All Sponsors
    cursor = g.conn.execute("SELECT * FROM Sponsors INNER JOIN Companies ON Sponsors.companyid=Companies.id WHERE hostid=%s and eventname=%s",hostid,eventname)
    sponsors = []
    for result in cursor:
      s = dict(name=result['name'],id=result['id'])
      sponsors.append(s)
    cursor.close()

    #EventInfo
    cursor = g.conn.execute("SELECT * FROM Events INNER JOIN Locations ON Events.locationid=Locations.id WHERE hostid=%s and name=%s",hostid,eventname)
    result = cursor.fetchone()
    eventdata = dict(name=result['name'],hostid=result['hostid'],start=result['starttime'],end=result['endtime'],description=result['description'], locationid=result['locationid'], street=result['street'], city=result['city'],state=result['state'],zipcode=result['zipcode'])
    cursor.close()

    context = dict(companyid=companyid, sponsors=sponsors, going=going, interested=interested, status=status, data=eventdata)

    return render_template("eventprofileC.html",**context)

@app.route('/<username>/groupprofile/<groupname>')
def groupprofile(username, groupname):
    
    #Groups(name, managerid, managerfirst, managerlast, description)
    
    #Data
    cursor = g.conn.execute("SELECT * FROM (Groups INNER JOIN Users ON Groups.managerid=Users.username) AS G WHERE G.name = %s",groupname)
    result = cursor.fetchone()
    groupdata = dict(name=result['name'], managerid=result['managerid'], managerfirst=result['firstname'], managerlast=result['lastname'], description=result['description'])
    
    #Tags
    tags = []
    cursor2 = g.conn.execute('SELECT * FROM Tags INNER JOIN Categories ON Tags.categoryid=Categories.id WHERE groupid=%s',groupname)
    for t in cursor2:
      tags.append(t['exercise_name'])
    cursor2.close()
    
    #Members
    members = []
    cursor = g.conn.execute("SELECT * FROM (Members LEFT OUTER JOIN (SELECT user1id, user2id FROM Friends WHERE user1id = %s) AS f ON Members.userid = f.user2id INNER JOIN Users ON Members.userid=Users.username) m WHERE groupid = %s ORDER BY m.user1id nulls last, userid",username,groupname)
    for r in cursor:
      d = dict(firstname=r['firstname'], lastname=r['lastname'], userid=r['username'])
      members.append(d)
    cursor.close()

    #checkMembership
    cursor = g.conn.execute("SELECT COUNT(*) FROM Members WHERE groupid=%s AND userid=%s",groupname,username)
    status = cursor.fetchone()[0]
    cursor.close()
    
    #Upcoming Events(userid, name, host, status, start, end, description, friends)
    events = []
    cursor = g.conn.execute("SELECT * FROM Events LEFT OUTER JOIN (SELECT * FROM UserParticipates WHERE userid = %s) as U ON Events.hostid = U.hostid AND Events.name = U.eventname WHERE Events.hostid = %s AND Events.endtime >= now() ORDER BY Events.starttime asc", username, groupname)
    for result in cursor:
      data = dict(userid=result['userid'],name=result['name'],host=result['hostid'],status=result['status'],start=result['starttime'],end=result['endtime'],description=result['description'])
      cursor2 = g.conn.execute("SELECT COUNT(*) AS friends FROM Events AS E INNER JOIN UserParticipates AS U ON E.hostid = U.hostid AND E.name = U.eventname WHERE U.userid IN (SELECT user2id FROM Friends WHERE user1id = %s) AND E.name = %s AND E.hostid = %s",username,data['name'],data['host'])
      numfriends = 0
      for r in cursor2:
          numfriends = r['friends']
      data['friends']=numfriends
      cursor2.close()
      events.append(data)
    cursor.close()
    
    #Posts(id, userid, text, group)
    cursor = g.conn.execute("SELECT * FROM (User_Posts INNER JOIN Posts ON User_Posts.postid = Posts.id INNER JOIN Users ON User_Posts.userid=Users.username) AS P WHERE P.groupid=%s AND P.responseto is null ORDER BY P.timestamp DESC LIMIT 15",groupname)
    messages = []
    for result in cursor:
        data = dict(id=result['postid'], firstname=result['firstname'], lastname=result['lastname'], userid=result['userid'],text=result['text'],group=result['groupid'])
        if username==result['userid']:
          data['owner'] = 1
        else:
          data['owner'] = 0 
        cursor2 = g.conn.execute("SELECT * FROM Posts AS P WHERE P.responseto = %s ORDER BY P.timestamp ASC",data['id'])
        comments = []
        for r in cursor2:
            r2 = g.conn.execute("SELECT * FROM Company_Posts INNER JOIN Companies ON Company_Posts.companyid=Companies.id WHERE postid=%s",r['id'])
            cp = r2.fetchone()
            r3 = g.conn.execute("SELECT * FROM User_Posts INNER JOIN Users ON User_Posts.userid=Users.username WHERE postid=%s",r['id'])
            up = r3.fetchone()
            if cp is not None:
              data2 = dict(id=r['id'], firstname=cp['name'], lastname="", userid=cp['companyid'], text=r['text'], group=None)
              data2['owner'] = 0
              comments.append(data2)
            if up is not None:
              data2 = dict(id=r['id'], firstname=up['firstname'], lastname=up['lastname'], userid=up['userid'], text=r['text'], group=up['groupid'])
              comments.append(data2)
              if username==up['userid']:
                data2['owner'] = 1
              else:
                data2['owner'] = 0 
            r2.close()
            r3.close()
        cursor2.close()
        post = dict(original=data, comments=comments)
        messages.append(post)
    cursor.close()

    context = dict(posts = messages, events = events, status = status, members=members, tags = tags, user=username, data=groupdata)
    
    return render_template("groupprofile.html",**context)

@app.route('/<int:companyid>/groupprofileC/<groupname>')
def groupprofileC(companyid, groupname):
    
    #Groups(name, managerid, managerfirst, managerlast, description)
    
    #Data
    cursor = g.conn.execute("SELECT * FROM (Groups INNER JOIN Users ON Groups.managerid=Users.username) AS G WHERE G.name = %s",groupname)
    result = cursor.fetchone()
    groupdata = dict(name=result['name'], managerid=result['managerid'], managerfirst=result['firstname'], managerlast=result['lastname'], description=result['description'])
    
    #Tags
    tags = []
    cursor2 = g.conn.execute('SELECT * FROM Tags INNER JOIN Categories ON Tags.categoryid=Categories.id WHERE groupid=%s',groupname)
    for t in cursor2:
      tags.append(t['exercise_name'])
    cursor2.close()
    
    #Members
    members = []
    cursor = g.conn.execute("SELECT * FROM Members INNER JOIN Users ON Members.userid = Users.username  WHERE groupid = %s ORDER BY username",groupname)
    for r in cursor:
      d = dict(firstname=r['firstname'], lastname=r['lastname'], userid=r['username'])
      members.append(d)
    cursor.close()
    
    #Upcoming Events(userid, name, host, status, start, end, description, friends)
    events = []
    cursor = g.conn.execute("SELECT * FROM Events WHERE hostid=%s ORDER BY Events.starttime asc", groupname)
    for result in cursor:
      data = dict(name=result['name'],host=result['hostid'],start=result['starttime'],end=result['endtime'],description=result['description'])
      events.append(data)
    cursor.close()
    
    #Posts(id, userid, text, group)
    cursor = g.conn.execute("SELECT * FROM (User_Posts INNER JOIN Posts ON User_Posts.postid = Posts.id INNER JOIN Users ON User_Posts.userid=Users.username) AS P WHERE P.groupid=%s AND P.responseto is null ORDER BY P.timestamp DESC LIMIT 15",groupname)
    messages = []
    for result in cursor:
        data = dict(id=result['postid'], firstname=result['firstname'], lastname=result['lastname'], userid=result['userid'],text=result['text'],group=result['groupid'])
        data['owner'] = 0
        cursor2 = g.conn.execute("SELECT * FROM Posts AS P WHERE P.responseto = %s ORDER BY P.timestamp ASC",data['id'])
        comments = []
        for r in cursor2:
            r2 = g.conn.execute("SELECT * FROM Company_Posts INNER JOIN Companies ON Company_Posts.companyid=Companies.id WHERE postid=%s",r['id'])
            cp = r2.fetchone()
            r3 = g.conn.execute("SELECT * FROM User_Posts INNER JOIN Users ON User_Posts.userid=Users.username WHERE postid=%s",r['id'])
            up = r3.fetchone()
            if cp is not None:
              data2 = dict(id=r['id'], firstname=cp['name'], lastname="", userid=cp['companyid'], text=r['text'], group=None)
              if companyid==cp['companyid']:
                data2['owner'] = 1
              else:
                data2['owner'] = 0
              comments.append(data2)
            if up is not None:
              data2 = dict(id=r['id'], firstname=up['firstname'], lastname=up['lastname'], userid=up['userid'], text=r['text'], group=up['groupid'])
              comments.append(data2)
              if username==up['userid']:
                data2['owner'] = 1
              else:
                data2['owner'] = 0 
            r2.close()
            r3.close()
        cursor2.close()
        post = dict(original=data, comments=comments)
        messages.append(post)
    cursor.close()

    context = dict(posts = messages, events = events, members=members, tags = tags, companyid=companyid, data=groupdata)
    
    return render_template("groupprofileC.html",**context)

@app.route('/<username>/companyprofile/<int:companyid>')
def companyprofile(username, companyid):
    #Company Info
    cursor = g.conn.execute("SELECT * FROM Companies WHERE id = %s", companyid)
    res = cursor.fetchone()
    companydata = dict(companyid=res['id'], name = res['name'], industry = res['industry'], commodities=res['commodities'])

    #Retails
    retails = []
    cursor = g.conn.execute("SELECT * FROM Companies INNER JOIN Retails ON Companies.id=Retails.companyid INNER JOIN Locations ON Locations.id = Retails.locationid WHERE companyid=%s",companyid)
    for result in cursor:
      data = dict(locationid=result['locationid'], street=result['street'], city=result['city'],state=result['state'],zipcode=result['zipcode'])
      retails.append(data)

    #Sponsored Events
    events = []
    cursor = g.conn.execute("SELECT * FROM Companies INNER JOIN Sponsors ON Companies.id=Sponsors.companyid INNER JOIN Events ON Sponsors.eventname=Events.name and Sponsors.hostid=Events.hostid WHERE Sponsors.companyid=%s",companyid)
    for result in cursor:
      data = dict(name=result['name'],host=result['hostid'],start=result['starttime'],end=result['endtime'],description=result['description'])
      cursor3 = g.conn.execute("SELECT * FROM UserParticipates WHERE userid=%s and hostid=%s and eventname=%s",username,result['hostid'],result['name'])
      s = cursor3.fetchone()
      if s is not None:
        s = s[0]
      else:
        s = "None"
      data['status']= s
      cursor3.close()
      events.append(data)

    #Posts
    cursor = g.conn.execute("SELECT * FROM (Company_Posts INNER JOIN Posts ON Company_Posts.postid = Posts.id INNER JOIN Companies ON Company_Posts.companyid=Companies.id) AS P WHERE P.companyid=%s AND P.responseto is null ORDER BY P.timestamp DESC LIMIT 15",companyid)
    messages = []
    for result in cursor:
        data = dict(id=result['postid'], firstname=result['name'], lastname="", userid=result['companyid'], text=result['text'], group=None)
        data['owner'] = 0
        cursor2 = g.conn.execute("SELECT * FROM Posts AS P WHERE P.responseto = %s ORDER BY P.timestamp ASC",data['id'])
        comments = []
        for r in cursor2:
            r2 = g.conn.execute("SELECT * FROM Company_Posts INNER JOIN Companies ON Company_Posts.companyid=Companies.id WHERE postid=%s",r['id'])
            cp = r2.fetchone()
            r3 = g.conn.execute("SELECT * FROM User_Posts INNER JOIN Users ON User_Posts.userid=Users.username WHERE postid=%s",r['id'])
            up = r3.fetchone()
            if cp is not None:
              data2 = dict(id=r['id'], firstname=cp['name'], lastname="", userid=cp['companyid'], text=r['text'], group=None)
              data2['owner'] = 0
              comments.append(data2)
            if up is not None:
              data2 = dict(id=r['id'], firstname=up['firstname'], lastname=up['lastname'], userid=up['userid'], text=r['text'], group=up['groupid'])
              comments.append(data2)
              if username==up['userid']:
                data2['owner'] = 1
              else:
                data2['owner'] = 0 
            r2.close()
            r3.close()
        cursor2.close()
        post = dict(original=data, comments=comments)
        messages.append(post)
    cursor.close()

    context = dict(data=companydata, retails=retails, events=events, posts=messages, user=username)

    return render_template("companyprofile.html",**context)

@app.route('/companyprofileC/<int:companyid>')
def companyprofileC(companyid):
    #Company Info
    cursor = g.conn.execute("SELECT * FROM Companies WHERE id = %s", companyid)
    res = cursor.fetchone()
    companydata = dict(companyid=res['id'], name = res['name'], industry = res['industry'], commodities=res['commodities'])

    #Retails
    retails = []
    cursor = g.conn.execute("SELECT * FROM Companies INNER JOIN Retails ON Companies.id=Retails.companyid INNER JOIN Locations ON Locations.id = Retails.locationid WHERE companyid=%s",companyid)
    for result in cursor:
      data = dict(locationid=result['locationid'], street=result['street'], city=result['city'],state=result['state'],zipcode=result['zipcode'])
      retails.append(data)

    #Sponsored Events
    events = []
    cursor = g.conn.execute("SELECT * FROM Companies INNER JOIN Sponsors ON Companies.id=Sponsors.companyid INNER JOIN Events ON Sponsors.eventname=Events.name and Sponsors.hostid=Events.hostid WHERE Sponsors.companyid=%s",companyid)
    for result in cursor:
      data = dict(name=result['name'],host=result['hostid'],start=result['starttime'],end=result['endtime'],description=result['description'])
      events.append(data)

    #Posts
    cursor = g.conn.execute("SELECT * FROM (Company_Posts INNER JOIN Posts ON Company_Posts.postid = Posts.id INNER JOIN Companies ON Company_Posts.companyid=Companies.id) AS P WHERE P.companyid=%s AND P.responseto is null ORDER BY P.timestamp DESC LIMIT 15",companyid)
    messages = []
    for result in cursor:
        data = dict(id=result['postid'], firstname=result['name'], lastname="", userid=result['companyid'], text=result['text'], group=None)
        data['owner']=1
        cursor2 = g.conn.execute("SELECT * FROM Posts AS P WHERE P.responseto = %s ORDER BY P.timestamp ASC",data['id'])
        comments = []
        for r in cursor2:
            r2 = g.conn.execute("SELECT * FROM Company_Posts INNER JOIN Companies ON Company_Posts.companyid=Companies.id WHERE postid=%s",r['id'])
            cp = r2.fetchone()
            r3 = g.conn.execute("SELECT * FROM User_Posts INNER JOIN Users ON User_Posts.userid=Users.username WHERE postid=%s",r['id'])
            up = r3.fetchone()
            if cp is not None:
              data2 = dict(id=r['id'], firstname=cp['name'], lastname="", userid=cp['companyid'], text=r['text'], group=None)
              if companyid==cp['companyid']:
                data2['owner'] = 1
              else:
                data2['owner'] = 0
              comments.append(data2)
            if up is not None:
              data2 = dict(id=r['id'], firstname=up['firstname'], lastname=up['lastname'], userid=up['userid'], text=r['text'], group=up['groupid'])
              comments.append(data2)
              data2['owner'] = 0 
            r2.close()
            r3.close()
        cursor2.close()
        post = dict(original=data, comments=comments)
        messages.append(post)
    cursor.close()

    context = dict(data=companydata, retails=retails, events=events, posts=messages, companyid=companyid)

    return render_template("companyprofileC.html",**context)

@app.route('/<username>/addCategory', methods=['POST'])
def addCategory(username):
    name = request.form['name']
    description = request.form['description']
    try:
      g.conn.execute('INSERT INTO Categories(exercise_name,description) VALUES (%s,%s)',name,description)   
    except exc.SQLAlchemyError:
      pass 
      
    return redirect(url_for('createGroupForm',username=username))

@app.route('/<username>/addCategoryE/<groupname>', methods=['POST'])
def addCategoryE(username,groupname):
    name = request.form['name']
    description = request.form['description']
    try:
      g.conn.execute('INSERT INTO Categories(exercise_name,description) VALUES (%s,%s)',name,description)   
    except exc.SQLAlchemyError:
      pass 

    return redirect(url_for('editGroupForm',username=username,groupname=groupname))

@app.route('/<username>/createGroupForm')
def createGroupForm(username):
    #AllTags
    tags = []
    cursor2 = g.conn.execute('SELECT * FROM Categories')
    for t in cursor2:
      tags.append(dict(name=t['exercise_name'],description=t['description']))
    cursor2.close()
    context = dict(user=username, tags=tags)
    return render_template('createGroup.html',**context)

@app.route('/<username>/editGroupForm/<groupname>')
def editGroupForm(username,groupname):
    
    #AllTags
    tagoptions = []
    cursor2 = g.conn.execute('SELECT * FROM Categories')
    for t in cursor2:
      r = g.conn.execute('SELECT COUNT(*) FROM Tags WHERE categoryid=%s and groupid=%s',t['id'], groupname)
      num = r.fetchone()[0]
      tagoptions.append(dict(status=num,name=t['exercise_name'],description=t['description']))
    cursor2.close()

    #Data
    cursor = g.conn.execute("SELECT * FROM Groups WHERE name = %s",groupname)
    result = cursor.fetchone()
    groupdata = dict(name=result['name'], managerid=result['managerid'], description=result['description'])
    
    #Tags
    tags = []
    cursor2 = g.conn.execute('SELECT * FROM Tags INNER JOIN Categories ON Tags.categoryid=Categories.id WHERE groupid=%s',groupname)
    for t in cursor2:
      tags.append(t['exercise_name'])
    cursor2.close()

    #Events(userid, name, host, status, start, end, description, friends)
    events = []
    cursor = g.conn.execute("SELECT * FROM Events INNER JOIN Locations ON Events.locationid=Locations.id WHERE Events.hostid = %s ORDER BY Events.starttime asc", groupname)
    for result in cursor:
      data = dict(name=result['name'],hostid=result['hostid'],description=result['description'], locationid=result['locationid'], street=result['street'], city=result['city'],state=result['state'],zipcode=result['zipcode'])
      start = str(result['starttime'])
      start = start.replace(' ','T')
      end = str(result['endtime'])
      end = end.replace(' ','T')
      data['start']=start
      data['end']=end
      events.append(data)
    cursor.close()

    context = dict(user=username, tagoptions=tagoptions, tags=tags, events=events, data=groupdata)
    return render_template('editGroup.html',**context)

@app.route('/<username>/createGroup', methods=['POST'])
def createGroup(username):
    name = request.form['name']
    description = request.form['text']
    url = url_for("createGroupForm",username=username)
    try:
      g.conn.execute('INSERT INTO Groups(name,managerid,description) VALUES (%s,%s,%s)',name,username,description)   

      tags = request.form.getlist('tag')

      for t in tags:
        cursor2 = g.conn.execute('SELECT id FROM Categories WHERE exercise_name=%s',t)
        tagid = cursor2.fetchone()[0]
        cursor2.close()
        g.conn.execute('INSERT INTO Tags (groupid, categoryid) VALUES(%s,%s)', name, tagid)

        #Become first member
      g.conn.execute('INSERT INTO Members(groupid,userid) VALUES(%s,%s)',name,username)
      url=url_for('groupprofile',username=username,groupname=name)
    except exc.SQLAlchemyError:
      pass
    return redirect(url)

@app.route('/<username>/createEvent/<hostid>', methods=['POST'])
def createEvent(username,hostid):
    name = request.form['name']
    description = request.form['text']
    start = request.form['start']
    end = request.form['end']
    street = request.form['street']
    city = request.form['city']
    state = request.form['state']
    zipcode = request.form['zipcode']
    url = url_for("editGroupForm",username=username,groupname=hostid)
    cursor2 = g.conn.execute('SELECT id FROM Locations WHERE street =%s and city=%s and state=%s and zipcode = %s',street,city,state,zipcode)
    insert = cursor2.fetchone()
    
    try:
      if insert is None:
        cursor = g.conn.execute('INSERT INTO Locations(street,city,state,zipcode) VALUES(%s,%s,%s,%s) RETURNING id',street,city,state,zipcode)
        insert = cursor.fetchone();
        cursor.close()
      cursor2.close()
      locationid = insert[0]

      g.conn.execute('INSERT INTO Events(name,hostid,description, starttime, endtime, locationid) VALUES (%s,%s,%s,%s,%s,%s)',name,hostid,description,start,end,locationid)   
      url = url_for('eventprofile',username=username,eventname=name,hostid=hostid)
    except exc.SQLAlchemyError:
      pass
    return redirect(url)

@app.route('/createUser', methods=['POST'])
def createUser():
    username = request.form['username']
    password = request.form['password']
    firstname = request.form['firstname']
    lastname = request.form['lastname']
    email = request.form['email']
    age = request.form['age']
    gender = request.form['gender']
    city = request.form['city']
    state = request.form['state']

    url = url_for("createUserForm")

    cursor2 = g.conn.execute('SELECT id FROM Locations WHERE street is null and city=%s and state=%s and zipcode is null',city,state)
    insert = cursor2.fetchone()
    try:
      if insert is None:
        cursor = g.conn.execute('INSERT INTO Locations(city,state) VALUES(%s,%s) RETURNING id',city,state)
        insert = cursor.fetchone();
        cursor.close()
      cursor2.close()
      locationid = insert[0]
      
      g.conn.execute('INSERT INTO Users(username, password, firstname, lastname, email, age, gender, locationid) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',username, password, firstname, lastname, email, age, gender, locationid)   
      url = '/'
    except exc.SQLAlchemyError:
      pass

    return redirect(url)

@app.route('/createCompany', methods=['POST'])
def createCompany():
    name = request.form['name']
    industry = request.form['industry']
    commodities = request.form['commodities']
    if commodities=="":
      commodities=None
    try:
      g.conn.execute('INSERT INTO Companies(name, industry, commodities) VALUES (%s,%s,%s)',name, industry, commodities)   
    except exc.SQLAlchemyError:
      pass
    return redirect(url_for('companyView'))

@app.route('/addRetail/<int:companyid>', methods=['POST'])
def addRetail(companyid):
    street = request.form['street']
    city = request.form['city']
    state = request.form['state']
    zipcode = request.form['zipcode']

    cursor = g.conn.execute('SELECT id FROM Locations WHERE street=%s and city=%s and state=%s and zipcode=%s',street,city,state,zipcode)
    insert = cursor.fetchone()
    try:
      if insert is None:
        cursor2 = g.conn.execute('INSERT INTO Locations(street,city,state,zipcode) VALUES(%s,%s,%s,%s) RETURNING id',street,city,state,zipcode)
        insert = cursor2.fetchone()
        cursor2.close()
      cursor.close()

      locationid = insert[0]
      g.conn.execute('INSERT INTO Retails(companyid, locationid) VALUES (%s,%s)',companyid,locationid)   
    except exc.SQLAlchemyError:
      pass

    return redirect(url_for('companyprofileC',companyid=companyid))


@app.route('/<username>/updateGroup/<groupname>', methods=['POST'])
def updateGroup(username,groupname):
    userid2 = request.form['managerid']
    description = request.form['text']
    try:
      g.conn.execute('UPDATE Groups SET managerid=%s, description=%s WHERE name=%s',userid2,description,groupname)   
    except exc.SQLAlchemyError:
      pass

    tags = request.form.getlist('tag')

    g.conn.execute('DELETE FROM Tags WHERE groupid=%s',groupname)   

    for t in tags:
      cursor2 = g.conn.execute('SELECT id FROM Categories WHERE exercise_name=%s',t)
      tagid = cursor2.fetchone()[0]
      cursor2.close()
      try:
        g.conn.execute('INSERT INTO Tags (groupid, categoryid) VALUES(%s,%s)', groupname, tagid)
      except exc.SQLAlchemyError:
        pass
    return redirect(url_for("editGroupForm",username=username, groupname=groupname))

@app.route('/<username>/updateEvent/<hostid>/<eventname>', methods=['POST'])
def updateEvent(username,hostid,eventname):
    description = request.form['text']
    start = request.form['start']
    end = request.form['end']
    street = request.form['street']
    city = request.form['city']
    state = request.form['state']
    zipcode = request.form['zipcode']

    cursor2 = g.conn.execute('SELECT id FROM Locations WHERE street =%s and city=%s and state=%s and zipcode = %s',street,city,state,zipcode)
    insert = cursor2.fetchone()
    try:
      if insert is None:
        cursor = g.conn.execute('INSERT INTO Locations(street,city,state,zipcode) VALUES(%s,%s,%s,%s) RETURNING id',street,city,state,zipcode)
        insert = cursor.fetchone();
        cursor.close()
      cursor2.close()
      locationid = insert[0]

      g.conn.execute('UPDATE Events SET description=%s, starttime=%s, endtime=%s, locationid=%s WHERE name=%s and hostid=%s',description,start,end,locationid,eventname,hostid)   
    except exc.SQLAlchemyError:
      pass
    return redirect(url_for("editGroupForm",username=username, groupname=hostid))

@app.route('/<username>/deleteGroup/<groupname>', methods=['POST'])
def deleteGroup(username,groupname):
    g.conn.execute('DELETE FROM Groups WHERE name=%s',groupname)    
    return redirect(url_for('home',username=username))

@app.route('/<int:companyid>/deleteRetail/<locationid>', methods=['POST'])
def deleteRetail(companyid,locationid):
    g.conn.execute('DELETE FROM Retails WHERE locationid=%s AND companyid=%s',locationid,companyid)    
    return redirect(url_for('companyprofileC',companyid=companyid))

@app.route('/<username>/deleteStatus/<hostid>/<eventname>', methods=['POST'])
def deleteStatus(username,hostid,eventname):
    g.conn.execute('DELETE FROM UserParticipates WHERE userid=%s and eventname=%s and hostid=%s',username,eventname,hostid)    
    return redirect(url_for('eventprofile',username=username,hostid=hostid,eventname=eventname))

@app.route('/<username>/updateStatus/<status>/<hostid>/<eventname>', methods=['POST'])
def updateStatus(username,status,hostid,eventname):
    try:
      g.conn.execute('UPDATE UserParticipates SET status=%s WHERE userid=%s and eventname=%s and hostid=%s',status,username,eventname,hostid)    
    except exc.SQLAlchemyError:
      pass
    return redirect(url_for('eventprofile',username=username,hostid=hostid,eventname=eventname))

@app.route('/<username>/addStatus/<status>/<hostid>/<eventname>', methods=['POST'])
def addStatus(username,status,hostid,eventname):
    try:
      g.conn.execute('INSERT INTO UserParticipates(status,userid,eventname,hostid) VALUES(%s,%s,%s,%s)',status,username,eventname,hostid)    
    except exc.SQLAlchemyError:
      pass
    return redirect(url_for('eventprofile',username=username,hostid=hostid,eventname=eventname))

@app.route('/<int:companyid>/deleteSponsor/<hostid>/<eventname>', methods=['POST'])
def deleteSponsor(companyid,hostid,eventname):
    g.conn.execute('DELETE FROM Sponsors WHERE companyid=%s and eventname=%s and hostid=%s',companyid,eventname,hostid)    
    return redirect(url_for('eventprofileC',companyid=companyid,hostid=hostid,eventname=eventname))

@app.route('/<int:companyid>/addSponsor/<hostid>/<eventname>', methods=['POST'])
def addSponsor(companyid,hostid,eventname):
    contribution = request.form['contribution']
    try:
      g.conn.execute('INSERT INTO Sponsors(companyid,eventname,hostid,contribution) VALUES(%s,%s,%s,%s)',companyid,eventname,hostid,contribution)    
    except exc.SQLAlchemyError:
      pass
    return redirect(url_for('eventprofileC',companyid=companyid,hostid=hostid,eventname=eventname))

@app.route('/<username>/addFriend/<usernamefriend>', methods=['POST'])
def addFriend(username,usernamefriend):
    try:
      g.conn.execute('INSERT INTO Friends(user1id,user2id) VALUES (%s,%s)',username,usernamefriend)   
    except exc.SQLAlchemyError:
      pass
    return redirect(url_for('userprofile',username=username,pusername=usernamefriend))

@app.route('/<username>/removeFriend/<usernamefriend>', methods=['POST'])
def removeFriend(username,usernamefriend):
    g.conn.execute('DELETE FROM Friends WHERE user1id=%s AND user2id=%s',username,usernamefriend)    
    return redirect(url_for('home',username=username))

@app.route('/<username>/removeFriend/<usernamefriend>/<pusername>', methods=['POST'])
def removeFriendP(username,usernamefriend,pusername):
    g.conn.execute('DELETE FROM Friends WHERE user1id=%s AND user2id=%s',username,usernamefriend)    
    return redirect(url_for('userprofile',username=username,pusername=pusername))

@app.route('/<username>/deleteEvent/<hostid>/<name>', methods=['POST'])
def deleteEvent(username,hostid,name):
    g.conn.execute('DELETE FROM Events WHERE hostid=%s AND name=%s',hostid,name)    
    return redirect(url_for('editGroupForm',username=username,groupname=hostid))


@app.route('/<username>/joinGroup/<groupname>', methods=['POST'])
def joinGroup(username,groupname):
    try:
      g.conn.execute('INSERT INTO Members(userid,groupid) VALUES (%s,%s)',username,groupname)   
    except exc.SQLAlchemyError:
      pass
    return redirect(url_for('groupprofile',username=username,groupname=groupname))

@app.route('/<username>/leaveGroup/<groupname>', methods=['POST'])
def leaveGroup(username,groupname):
    g.conn.execute('DELETE FROM Members WHERE userid=%s AND groupid=%s',username,groupname)    
    return redirect(url_for('groupprofile',username=username, groupname=groupname))


@app.route('/<username>/searchEvent', methods=['POST'])
def searchEvent(username):
    method = request.form['searchBy']
    search = request.form['Search']
    events = []

    #Search by Name(name, hostid, description, start, end, locationid, street, city, state, zipcode)
    if method=='name':
      cursor = g.conn.execute("SELECT * FROM Events INNER JOIN Locations ON Events.locationid=Locations.id WHERE name LIKE concat(\'%%\',%s,\'%%\') ORDER BY starttime",search)
      for result in cursor:
        eventdata = dict(name=result['name'],hostid=result['hostid'],start=result['starttime'],end=result['endtime'],description=result['description'], locationid=result['locationid'], street=result['street'], city=result['city'],state=result['state'],zipcode=result['zipcode'])
        cursor2 = g.conn.execute("SELECT COUNT(*) AS friends FROM Events AS E INNER JOIN UserParticipates AS U ON E.hostid = U.hostid AND E.name = U.eventname WHERE U.userid IN (SELECT user2id FROM Friends WHERE user1id = %s) AND E.name = %s AND E.hostid = %s",username,eventdata['name'],eventdata['hostid'])
        numfriends = 0
        for r in cursor2:
            numfriends = r['friends']
        eventdata['friends']=numfriends
        cursor2.close()
        cursor3 = g.conn.execute("SELECT * FROM UserParticipates WHERE userid=%s and hostid=%s and eventname=%s",username,result['hostid'],result['name'])
        s = cursor3.fetchone()
        if s is not None:
          s = s[0]
        eventdata['status']= s
        events.append(eventdata)
        cursor3.close()
      cursor.close()

    #Search by Description(name, hostid, description, start, end, locationid, street, city, state, zipcode)
    if method=='description':
      cursor = g.conn.execute("SELECT * FROM Events INNER JOIN Locations ON Events.locationid=Locations.id WHERE description LIKE concat(\'%%\',%s,\'%%\') ORDER BY starttime",search)
      for result in cursor:
        eventdata = dict(name=result['name'],hostid=result['hostid'],start=result['starttime'],end=result['endtime'],description=result['description'], locationid=result['locationid'], street=result['street'], city=result['city'],state=result['state'],zipcode=result['zipcode'])
        cursor3 = g.conn.execute("SELECT * FROM UserParticipates WHERE userid=%s and hostid=%s and eventname=%s",username,result['hostid'],result['name'])
        cursor2 = g.conn.execute("SELECT COUNT(*) AS friends FROM Events AS E INNER JOIN UserParticipates AS U ON E.hostid = U.hostid AND E.name = U.eventname WHERE U.userid IN (SELECT user2id FROM Friends WHERE user1id = %s) AND E.name = %s AND E.hostid = %s",username,eventdata['name'],eventdata['hostid'])
        numfriends = 0
        for r in cursor2:
            numfriends = r['friends']
        eventdata['friends']=numfriends
        s = cursor3.fetchone()
        if s is not None:
          s = s[0]
        eventdata['status']= s
        events.append(eventdata)
        cursor2.close()
        cursor3.close()
      cursor.close()

    #Search by Group(name, hostid, description, start, end, locationid, street, city, state, zipcode)
    if method=='group':
      cursor = g.conn.execute("SELECT * FROM Events INNER JOIN Locations ON Events.locationid=Locations.id WHERE hostid LIKE concat(\'%%\',%s,\'%%\')",search)
      for result in cursor:
        eventdata = dict(name=result['name'],hostid=result['hostid'],start=result['starttime'],end=result['endtime'],description=result['description'], locationid=result['locationid'], street=result['street'], city=result['city'],state=result['state'],zipcode=result['zipcode'])
        cursor3 = g.conn.execute("SELECT * FROM UserParticipates WHERE userid=%s and hostid=%s and eventname=%s",username,result['hostid'],result['name'])
        cursor2 = g.conn.execute("SELECT COUNT(*) AS friends FROM Events AS E INNER JOIN UserParticipates AS U ON E.hostid = U.hostid AND E.name = U.eventname WHERE U.userid IN (SELECT user2id FROM Friends WHERE user1id = %s) AND E.name = %s AND E.hostid = %s",username,eventdata['name'],eventdata['hostid'])
        numfriends = 0
        for r in cursor2:
            numfriends = r['friends']
        eventdata['friends']=numfriends
        s = cursor3.fetchone()
        if s is not None:
          s = s[0]
        eventdata['status']= s
        events.append(eventdata)
        cursor2.close()
        cursor3.close()
      cursor.close()

    context = dict(events=events, user=username)
    return render_template("eventsSearch.html",**context)

@app.route('/<int:companyid>/searchEventC', methods=['POST'])
def searchEventC(companyid):
    method = request.form['searchBy']
    search = request.form['Search']
    events = []

    #Search by Name(name, hostid, description, start, end, locationid, street, city, state, zipcode)
    if method=='name':
      cursor = g.conn.execute("SELECT * FROM Events INNER JOIN Locations ON Events.locationid=Locations.id WHERE name LIKE concat(\'%%\',%s,\'%%\')",search)
      for result in cursor:
        eventdata = dict(name=result['name'],hostid=result['hostid'],start=result['starttime'],end=result['endtime'],description=result['description'], locationid=result['locationid'], street=result['street'], city=result['city'],state=result['state'],zipcode=result['zipcode'])
        cursor2 = g.conn.execute("SELECT COUNT(*) FROM Sponsors WHERE companyid=%s AND eventname=%s AND hostid=%s",companyid,eventdata['name'],eventdata['hostid'])
        status = cursor2.fetchone()[0]
        eventdata['status']=status
        events.append(eventdata)
    cursor.close()

    #Search by Description(name, hostid, description, start, end, locationid, street, city, state, zipcode)
    if method=='description':
      cursor = g.conn.execute("SELECT * FROM Events INNER JOIN Locations ON Events.locationid=Locations.id WHERE description LIKE concat(\'%%\',%s,\'%%\')",search)
      for result in cursor:
        eventdata = dict(name=result['name'],hostid=result['hostid'],start=result['starttime'],end=result['endtime'],description=result['description'], locationid=result['locationid'], street=result['street'], city=result['city'],state=result['state'],zipcode=result['zipcode'])
        cursor2 = g.conn.execute("SELECT COUNT(*) FROM Sponsors WHERE companyid=%s AND eventname=%s AND hostid=%s",companyid,eventdata['name'],eventdata['hostid'])
        status = cursor2.fetchone()[0]
        eventdata['status']=status
        events.append(eventdata)
    cursor.close()

    #Search by Group(name, hostid, description, start, end, locationid, street, city, state, zipcode)
    if method=='group':
      cursor = g.conn.execute("SELECT * FROM Events INNER JOIN Locations ON Events.locationid=Locations.id WHERE hostid LIKE concat(\'%%\',%s,\'%%\')",search)
      for result in cursor:
        eventdata = dict(name=result['name'],hostid=result['hostid'],start=result['starttime'],end=result['endtime'],description=result['description'], locationid=result['locationid'], street=result['street'], city=result['city'],state=result['state'],zipcode=result['zipcode'])
        cursor2 = g.conn.execute("SELECT COUNT(*) FROM Sponsors WHERE companyid=%s AND eventname=%s AND hostid=%s",companyid,eventdata['name'],eventdata['hostid'])
        status = cursor2.fetchone()[0]
        eventdata['status']=status
        events.append(eventdata)
    cursor.close()

    context = dict(events=events, companyid=companyid)
    return render_template("eventsSearchC.html",**context)

@app.route('/<username>/searchGroup', methods=['POST'])
def searchGroup(username):
    method = request.form['searchBy']
    search = request.form['Search']
    groups = []

    #Search by Name(name, description, tags)
    if method=='name':
      cursor = g.conn.execute('SELECT * FROM Groups WHERE name LIKE concat(\'%%\',%s,\'%%\')',search)
      for result in cursor:
        tags = []
        cursor2 = g.conn.execute('SELECT * FROM Tags INNER JOIN Categories ON Tags.categoryid=Categories.id WHERE groupid=%s',result['name'])
        for t in cursor2:
          tags.append(t['exercise_name'])
        data = dict(name=result['name'],description=result['description'],tags=tags)
        groups.append(data)
        cursor2.close()
      cursor.close()

    #Search by Tag(name, description, tags)
    if method=='tag':
      cursor = g.conn.execute('SELECT * FROM (Tags INNER JOIN Groups ON Tags.groupid = Groups.name INNER JOIN Categories ON Tags.categoryid = Categories.id) AS S WHERE S.exercise_name LIKE concat(\'%%\',%s,\'%%\')',search)
      for result in cursor:
        tags = []
        cursor2 = g.conn.execute('SELECT * FROM Tags INNER JOIN Categories ON Tags.categoryid=Categories.id WHERE groupid=%s',result['name'])
        for t in cursor2:
          tags.append(t['exercise_name'])
        data = dict(name=result['name'],description=result['description'],tags=tags)
        groups.append(data)
        cursor2.close()
      cursor.close()

    #AllTags
    tags = []
    cursor2 = g.conn.execute('SELECT * FROM Categories')
    for t in cursor2:
      tags.append(dict(name=t['exercise_name'],description=t['description']))
    cursor2.close()

    context = dict(tags=tags, groups=groups, user=username)
    return render_template("groupsSearch.html",**context)

@app.route('/<username>/searchUser', methods=['POST'])
def searchUser(username):
    method = request.form['searchBy']
    search = request.form['Search']
    users = []

    #Search by Name(name, hostid, description, start, end, locationid, street, city, state, zipcode)
    if method=='name':
      cursor = g.conn.execute("SELECT * FROM Users INNER JOIN Locations ON Users.locationid=Locations.id WHERE concat(firstname,lastname) LIKE concat(\'%%\',%s,\'%%\')",search)
      for result in cursor:
        userdata = dict(username=result['username'],firstname=result['firstname'],lastname=result['lastname'],locationid=result['locationid'], street=result['street'], city=result['city'],state=result['state'],zipcode=result['zipcode'])
        users.append(userdata)
      cursor.close()

    #Search by Username(name, hostid, description, start, end, locationid, street, city, state, zipcode)
    if method=='username':
      cursor = g.conn.execute("SELECT * FROM Users INNER JOIN Locations ON Users.locationid=Locations.id WHERE username LIKE concat(\'%%\',%s,\'%%\')",search)
      for result in cursor:
        userdata = dict(username=result['username'],firstname=result['firstname'],lastname=result['lastname'],locationid=result['locationid'], street=result['street'], city=result['city'],state=result['state'],zipcode=result['zipcode'])
        users.append(userdata)
      cursor.close()

    # #Search by Username(name, hostid, description, start, end, locationid, street, city, state, zipcode)
    # if method=='location':
    #   cursor = g.conn.execute("SELECT * FROM Users INNER JOIN Locations ON Users.locationid=Locations.id WHERE username LIKE concat(\'%%\',%s,\'%%\')",search)
    #   for result in cursor:
    #     userdata = dict(username=result['username'],firstname=result['firstname'],lastname=result['lastname'],locationid=result['locationid'], street=result['street'], city=result['city'],state=result['state'],zipcode=result['zipcode'])
    #     users.append(userdata)
    # cursor.close()

    context = dict(users=users, user=username)
    return render_template("userSearch.html",**context)

@app.route('/<username>/searchCompany', methods=['POST'])
def searchCompany(username):
    method = request.form['searchBy']
    search = request.form['Search']
    companies = []

    #Search by Name(name,industry,commodities)
    if method=='name':
      cursor = g.conn.execute("SELECT * FROM Companies WHERE name LIKE concat(\'%%\',%s,\'%%\')",search)
      for res in cursor:
        companydata = dict(companyid=res['id'], name = res['name'], industry = res['industry'], commodities=res['commodities'])
        companies.append(companydata)
      cursor.close()

    #Search by Industry(name,industry,commodities)
    if method=='industry':
      cursor = g.conn.execute("SELECT * FROM Companies WHERE industry LIKE concat(\'%%\',%s,\'%%\')",search)
      for res in cursor:
        companydata = dict(companyid=res['id'], name = res['name'], industry = res['industry'], commodities=res['commodities'])
        companies.append(companydata)
      cursor.close()

    #Search by Commodities(name,industry,commodities)
    if method=='commodities':
      cursor = g.conn.execute("SELECT * FROM Companies WHERE commodities LIKE concat(\'%%\',%s,\'%%\')",search)
      for res in cursor:
        companydata = dict(companyid=res['id'], name = res['name'], industry = res['industry'], commodities=res['commodities'])
        companies.append(companydata)
      cursor.close()

    context = dict(user = username, companies=companies)

    return render_template("companySearch.html",**context)

@app.route('/<username>/addPost/<groupid>/<int:responseto>/<puser>/<int:companyid>', methods=['POST'])
def addPost(username,groupid,responseto,puser,companyid):
    url = None
    text = request.form['text']

    if groupid!='null':
      url = url_for('groupprofile',username=username,groupname=groupid)

    elif puser!='null':
      url = url_for('userprofile',username=username,pusername=puser)
    
    elif companyid!=0:
      url = url_for('companyprofile',username=username,companyid=companyid)
 
    else:
      url = url_for('home',username=username)
    
    try:
      if groupid=='null':
        if responseto==0:
          r = g.conn.execute('INSERT INTO Posts(text) VALUES (%s) RETURNING id',text)
          id = r.fetchone()[0]
          r.close()
          g.conn.execute('INSERT INTO User_Posts(postid,userid) VALUES(%s,%s)',id,username)    
        else:
          r = g.conn.execute('INSERT INTO Posts(responseto,text) VALUES (%s,%s) RETURNING id',(responseto,text))
          id = r.fetchone()[0]
          r.close()
          g.conn.execute('INSERT INTO User_Posts(postid,userid) VALUES(%s,%s)',(id,username))    
      
      else:
        if responseto==0:
          r = g.conn.execute('INSERT INTO Posts(text) VALUES (%s) RETURNING id',text)
          id = r.fetchone()[0]

          g.conn.execute('INSERT INTO User_Posts(postid,userid,groupid) VALUES(%s,%s,%s)',id,username,groupid)    
        else:
          r = g.conn.execute('INSERT INTO Posts(responseto,text) VALUES (%s,%s) RETURNING id',responseto,text)
          id = r.fetchone()[0]
          g.conn.execute('INSERT INTO User_Posts(postid,userid,groupid) VALUES(%s,%s,%s)',id,username,groupid)    
    except exc.SQLAlchemyError:
      pass

    return redirect(url)

@app.route('/<int:companyid>/addPostC/<int:responseto>/<groupname>', methods=['POST'])
def addPostC(companyid,responseto,groupname):
    text = request.form['text']
    url = url_for('companyprofileC',companyid=companyid)
    if groupname != "null":
        url = url_for('groupprofileC',companyid=companyid,groupname=groupname)

    try:
      if responseto==0:
        r = g.conn.execute('INSERT INTO Posts(text) VALUES (%s) RETURNING id',text)
        id = r.fetchone()[0]
        r.close()
        g.conn.execute('INSERT INTO Company_Posts(postid,companyid) VALUES(%s,%s)',id,companyid)    
      else:
        r = g.conn.execute('INSERT INTO Posts(responseto,text) VALUES (%s,%s) RETURNING id',responseto,text)
        id = r.fetchone()[0]
        r.close()
        g.conn.execute('INSERT INTO Company_Posts(postid,companyid) VALUES(%s,%s)',id,companyid)            
    except exc.SQLAlchemyError:
      pass
    return redirect(url)

@app.route('/<int:companyid>/deletePostC/<int:postid>/<groupname>/', methods=['POST'])
def deletePostC(companyid,postid,groupname):
    url = url_for('companyprofileC',companyid=companyid)
    if groupname != "null":
        url = url_for('groupprofileC',companyid=companyid,groupname=groupname)

    g.conn.execute('DELETE FROM Posts WHERE id=%s',postid)    
    return redirect(url)

@app.route('/<username>/deletePost/<int:postid>/<puser>/<groupname>/<int:companyid>', methods=['POST'])
def deletePost(username,postid,puser,groupname,companyid):
    url = url_for('home',username=username)
    if companyid > 0:
        url = url_for('companyprofile',username=username,companyid=companyid)
    elif groupname != "null":
        url = url_for('groupprofile',username=username,groupname=groupname)
    elif puser != "null":
        url = url_for('userprofile',username=username,pusername=puser)

    g.conn.execute('DELETE FROM Posts WHERE id=%s',postid)    
    return redirect(url)


@app.route('/login')
def login():
    abort(401)
    this_is_never_executed()


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python server.py

    Show the help text using:

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
