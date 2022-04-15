"""
Columbia W4111 Intro to databases
Example webserver
To run locally
    python server.py
Go to http://localhost:8111 in your browser
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import datetime
import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, url_for,session
import hashlib

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)



# XXX: The Database URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail
DB_USER = "px2143"
DB_PASSWORD = "px2143"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"
# DB_SERVER= "w4111-4-14.cisxo09blonu.us-east-1.rds.amazonaws.com"
DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/proj1part2"

#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)
metadata = MetaData(engine)

# Here we create a test table and insert some values in it
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")

app.secret_key = "projectw4111"

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request
  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None
  if request.path.startswith("/static"):
    return None
  if request.path in ["/","/login"]:
    return None
  if not session.get("username"):
    return redirect("/")


@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
# @app.route('/')
# def index():
#   """
#   request is a special object that Flask provides to access web request information:
#   request.method:   "GET" or "POST"
#   request.form:     if the browser submitted a form, this contains the data in the form
#   request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2
#   See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
#   """
#   print(request.args)
#
#   cursor = g.conn.execute("SELECT username FROM users")
#   names = []
#   for result in cursor:
#     names.append(result['username'])  # can also be accessed using result[0]
#   cursor.close()
#
#   context = dict(data = names)
#
#   return render_template("index.html", **context)
@app.route("/")
def loginpage():

  return render_template("login.html")


@app.route("/index")
def index():
  cursor = g.conn.execute("SELECT blogs.bid as bid ,title,concat(substring(content,1,300),'...') as content,"
                          "image,updatetime,username,avatar,types.tid as tid,types.name as typename, types.color as typecolor, "
                          "occupations.oid as oid,occupations.job as job "
                          "FROM blogs,users,types,blogs_own_types,occupations,users_have_occupations "
                          "where blogs.uid = users.uid and "
                          "blogs.bid=blogs_own_types.bid and blogs_own_types.tid = types.tid and "
                          "occupations.oid = users_have_occupations.oid and users_have_occupations.uid = users.uid ")
  blogs = cursor.fetchall()
  blogs.sort(key=lambda blog:blog["updatetime"],reverse=True)
  print(blogs[0]['oid'])
  return render_template("index.html",blogs=blogs)


@app.route("/login",methods=["post"])
def login():
  username = request.form["username"]
  password = hashlib.md5(request.form["password"].encode()).hexdigest()
  cursor = g.conn.execute("SELECT uid,username,password FROM users WHERE username = '{}' AND password='{}' ".format(username,password))
  results = cursor.fetchall()
  print(results)
  if results:
    uid = results[0]["uid"]
    session['username'] = username
    session['uid'] = uid
    return redirect("/index")
  else:
    error = "Username or password is wrong"
    return render_template("login.html",error=error)

@app.route("/release")
def releasepage():
  cursor = g.conn.execute("SELECT tid, name typename FROM types")
  types = cursor.fetchall()
  cursor = g.conn.execute("SELECT toid, name topicname FROM topics")
  topics = cursor.fetchall()
  return render_template("release.html",types=types,topics=topics)


# Example of adding new data to the database
@app.route('/release/submit', methods=['POST'])
def add():
  print(request.form)
  uid = session['uid']
  cursor = g.conn.execute("SELECT max(bid) FROM blogs")
  bid = cursor.fetchall()[0][0] + 1

  # cursor = g.conn.execute("SELECT avatar FROM users WHERE uid = {}".format(uid))
  # avatar = cursor.fetchall()[0][0]
  # print(avatar)

  title = request.form['title']
  content = request.form['content']
  tid = request.form['tid']
  toid = request.form['toid']
  image = request.form['image']

  createtime = datetime.datetime.now()
  updatetime = datetime.datetime.now()

  published = True if 'pulished' in request.form else False
  share = True if 'share' in request.form else False
  commentable = True if 'commentable' in request.form else False
  recommend = True if 'recommend' in request.form else False
  cmd = "INSERT INTO blogs(bid,title,content,image,createtime,updatetime,uid,share,recommend,commentable,published) " \
        "values(:bid, :title, :content, :image, :createtime,:updatetime, :uid, :share, :recommend,:commentable, :published)"
  g.conn.execute(text(cmd),bid=bid,title=title,content=content,image=image,createtime=createtime,updatetime=updatetime,
                 uid=uid,share=share,recommend=recommend,commentable=commentable,published=published)
  cmd = "insert into blogs_own_types(bid,tid) values(:bid, :tid)"
  g.conn.execute(text(cmd),bid=bid,tid=tid)
  cmd = "insert into blogs_own_topics(bid,toid) values(:bid, :toid)"
  g.conn.execute(text(cmd), bid=bid, toid=toid)


  return redirect('/index')

@app.route("/blog/<id>")
def blog(id):
  print(id)
  cursor = g.conn.execute("SELECT * FROM blogs inner join users on blogs.uid = users.uid where bid = '{}' ".format(id))
  results = cursor.fetchall()
  blog = dict(results[0])
  cursor = g.conn.execute("SELECT types.tid tid, types.name typename, types.color typecolor FROM blogs_own_types inner join types on blogs_own_types.tid = types.tid"
                          " where bid = '{}' ".format(id))
  types = dict(cursor.fetchall()[0])
  blog.update(types)
  cursor = g.conn.execute("SELECT topics.toid toid, topics.name topicname, topics.color topiccolor FROM blogs_own_topics inner join topics on blogs_own_topics.toid = topics.toid"
                          " where bid = '{}' ".format(id))
  topics = cursor.fetchall()
  # cursor = g.conn.execute("SELECT ")
  return render_template("blog.html",blog=blog,topics=topics)


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
    Run the server using
        python server.py
    Show the help text using
        python server.py --help
    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()