from flask import Flask, render_template, redirect, url_for, flash, request, make_response,jsonify,abort, send_file
from models import db, Poll, Vote
from forms import PollForm, VoteForm
import boto3
from config import REGION, USER_POOL_ID, CLIENT_ID, CLIENT_SECRET
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import hashlib
import hmac
from base64 import b64encode
import csv
import os
from sqlalchemy import event
from sqlalchemy.engine import Engine
#from sqlite3 import Connection as SQLite3Connection




app = Flask(__name__)
app.config.from_pyfile('config.py')

#@event.listens_for(Engine, "connect")
#def _set_sqlite_pragma(dbapi_connection, connection_record):
#    if isinstance(dbapi_connection, SQLite3Connection):
#        cursor = dbapi_connection.cursor()
#        cursor.execute("PRAGMA foreign_keys=ON;")
#        cursor.close()


db.init_app(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Cognito client
cognito = boto3.client('cognito-idp', region_name=REGION)


class User(UserMixin):
    def __init__(self, email, password):
        self.id = email
        self.password = password
        

    def __repr__(self):
        return "%s/%s" % (self.id, self.password)
    
def generate_secret_hash(username, client_id, client_secret):
    message = username + client_id
    dig = hmac.new(client_secret.encode('utf-8'), msg=message.encode('utf-8'), digestmod=hashlib.sha256).digest()
    return b64encode(dig).decode()


@login_manager.user_loader
def load_user(user_id):
    user = User(user_id, "dummy_password")
    return user
    


"""Defininig the routes for the application."""
"""The home route.  This route is accessible to all users.  It displays the home page."""
@app.route('/')
def home():
    return render_template('base.html')


"""The signup route.  This route is accessible to all users.  It displays the signup page."""""

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        secret_hash = generate_secret_hash(email, CLIENT_ID, CLIENT_SECRET)

        

        try:
            cognito.sign_up(
                ClientId=CLIENT_ID,
                Username=email,
                Password=password,
                SecretHash=secret_hash,
                UserAttributes=[{'Name': 'email', 'Value': email}]
            )
            cognito.admin_confirm_sign_up(
                UserPoolId=USER_POOL_ID,
                Username=email
            )
            return jsonify(message='Account created successfully'), 200
            
            
        except Exception as e:
            return jsonify(error=str(e)), 400

    return render_template('signup.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Parse the request data
        email = request.form['email']
        password = request.form['password']

        # Authenticate the user
        try:
            secret_hash = generate_secret_hash(email, CLIENT_ID, CLIENT_SECRET)
            response = cognito.initiate_auth(
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password,
                    'SECRET_HASH': secret_hash
                },
                ClientId=CLIENT_ID
            )

            # Log in the user
            user = User(email, password)
            login_user(user)

            flash('Logged in successfully!', 'success')
            return redirect(url_for('create_poll'))
        except Exception as e:
            error = str(e)

    return render_template('login.html', error=error)




"""The secure route.  This route is accessible only to authenticated users.  It displays a message."""""
@app.route('/secure')
def secure_route():
    return jsonify(message='This is a secure route accessible only by authenticated users.')

    


@app.route('/polls')
def list_polls():
    polls = Poll.query.all()
    return render_template('polls.html', polls=polls)


""" Only available to authorized users.It can be used to create polls."""
@app.route('/create-poll', methods=['GET', 'POST'])
@login_required
def create_poll():
    
    form = PollForm()
    if form.validate_on_submit():
        question = form.question.data
        choices = form.choices.data.splitlines()
        
        new_poll = Poll(question=question, user_id=current_user.id)
        db.session.add(new_poll)

        for choice in choices:
            new_vote = Vote(choice=choice, count=0, poll=new_poll)
            db.session.add(new_vote)

        db.session.commit()
        flash('Poll created successfully!', 'success')
        return redirect(url_for('list_polls'))

    return render_template('create_poll.html', form=form)


@app.route('/poll/<int:poll_id>', methods=['GET', 'POST'])
def vote_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    

    # Check if the current user is the poll's creator
    

    choices = [(vote.id, vote.choice) for vote in poll.votes]
    form = VoteForm()
    form.choice.choices = choices

    voted_cookie = f'voted_{poll_id}'

    if request.cookies.get(voted_cookie) :
        flash('You have already voted on this poll.', 'warning')
        return redirect(url_for('poll_results', poll_id=poll_id))

    if form.validate_on_submit() and form.choice.data:
        choice_id = form.choice.data
        vote = Vote.query.get(choice_id)
        if vote:
            vote.count += 1
            db.session.commit()

            response = make_response(redirect(url_for('poll_results', poll_id=poll_id)))
            response.set_cookie(voted_cookie, 'true', max_age=60*60*24*30)  # Expires in 30 days

            flash('Vote submitted successfully!', 'success')
            return response
    return render_template('vote_poll.html', poll=poll, form=form)


""" Only available to authorized users.  It can be used to edit polls."""
@app.route('/edit-poll/<int:poll_id>', methods=['GET', 'POST'])
@login_required
def edit_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)


    form = PollForm(obj=poll)

    if form.validate_on_submit():
        poll.question = form.question.data
        db.session.commit()
        flash('Poll updated successfully!', 'success')
        return redirect(url_for('list_polls'))

    return render_template('edit_poll.html', form=form, poll=poll)


  
@app.route('/poll/<int:poll_id>/results')
def poll_results(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    total_votes = sum(vote.count for vote in poll.votes)
    return render_template('poll_results.html', poll=poll, total_votes=total_votes)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html'), 404


@app.route('/polls/<int:poll_id>/delete', methods=['POST'])
@login_required
def delete_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    if poll.user_id != current_user.id:
        abort(403)
    # Delete related votes
    Vote.query.filter_by(poll_id=poll_id).delete()
    
    db.session.delete(poll)
    db.session.commit()
    flash('Poll deleted successfully.', 'success')
    return redirect(url_for('list_polls'))


@app.route('/poll/<int:poll_id>/download-stats', methods=['GET'])
@login_required
def download_stats(poll_id):
    poll = Poll.query.get_or_404(poll_id)

    if poll.user_id != current_user.id:
        abort(403)

    csv_filename = f"poll_{poll_id}_stats.csv"

    with open(csv_filename, mode='w', newline='') as csvfile:
        stats_writer = csv.writer(csvfile)
        stats_writer.writerow(['Choice', 'Vote Count'])

        for vote in poll.votes:
            stats_writer.writerow([vote.choice, vote.count])

    return_data = send_file(csv_filename, mimetype='text/csv', as_attachment=True, download_name=csv_filename)

    os.remove(csv_filename)  # Clean up the temporary file

    return return_data