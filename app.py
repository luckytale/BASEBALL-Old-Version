from flask import app
from flask import Flask, render_template, redirect, request, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, ForeignKey, Column
from sqlalchemy import String, Integer, CHAR
from sqlalchemy import Column
from sqlalchemy import func, asc, or_
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from itertools import groupby
from operator import itemgetter
from waitress import serve
import os
import json

app = Flask(__name__)
Base = declarative_base()
db = SQLAlchemy(model_class=Base)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blog.db"
app.config['SECRET_KEY'] = os.urandom(24)
db.init_app(app)

from flask_migrate import Migrate
migrate = Migrate(app, db)

#ログイン機能
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True)
    password = db.Column(db.String(20))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User(username=username, password=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    else:       
        return render_template("signup.html")

@app.route("/login", methods=['GET', 'POST']) 
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect('/')
        else:
            flash('ユーザー名またはパスワードが間違っています', 'error')
            return redirect('/login')
    else:       
        return render_template("login.html")

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect('/login')

class Bat(db.Model):
    __tablename__ = 'bat'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    matchnumber=db.Column(db.String(10))
    BatterName = db.Column(db.String(10))
    hand = db.Column(db.String(3))
    PitchType = db.Column(db.String(10))
    place = db.Column(db.String(10))
    Result = db.Column(db.String(10))
    course = db.Column(db.String(1))
    x = db.Column(db.String(10))
    y = db.Column(db.String(10))
    RBI = db.Column(db.String(1))

class Match(db.Model):
    __tablename__ = 'match'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    match_number = db.Column(db.Integer)
    date = db.Column(db.Date, default=func.current_date())
    matchType = db.Column(db.String(10))
    opponent = db.Column(db.String(20))

class Players(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uniform_number = db.Column(db.Integer)
    player= db.Column(db.String(10))

with app.app_context():
    db.create_all()

@app.route("/")
@login_required
def index():
    return render_template('index.html')

@app.route('/see', methods=['GET', 'POST'])
@login_required
def see():
    if request.method == 'GET':
        bats = Bat.query.filter_by(user_id=current_user.id).all()
        return render_template("see.html", bats=bats)

@app.route("/players", methods=['GET', 'POST'])
@login_required
def players():
    if request.method == "GET":
        players = Players.query.filter_by(user_id=current_user.id).all()
        return render_template('players.html', players=players)  
      
    if request.method == "POST":
        uniform_number= request.form.get('uniform_number')
        player= request.form.get('player')
        user_id= request.form.get('user_id')
        players = Players(user_id=user_id,
                          uniform_number=uniform_number,
                          player=player)
        db.session.add(players)
        db.session.commit()
        return redirect('/players')
    else:
        return render_template('players.html')

@app.route('/<int:id>/player_delete', methods=['GET'])
@login_required
def player_delete(id):
    players = Players.query.get(id)
    db.session.delete(players)
    db.session.commit()
    return redirect('/players')

@app.route("/register", methods=['GET', 'POST'])
@login_required
def register():
    default_match_number = session.get('matchnumber', '1')
    default_hand = session.get('hand', '右投')
    if request.method == 'GET':
        bats = Bat.query.filter_by(user_id=current_user.id).all()
        return render_template('register.html', bats=bats, default_match_number=default_match_number, default_hand=default_hand)

    if request.method == "POST":
        user_id= request.form.get('user_id')
        BatterName= request.form.get('BatterName')
        hand= request.form.get('hand', default_hand)
        PitchType= request.form.get('PitchType')
        Result= request.form.get('Result')
        course= request.form.get('course')
        x = request.form.get('x')
        y = request.form.get('y')
        RBI = request.form.get('RBI')
        place = request.form.get('place')
        matchnumber = request.form.get('matchnumber', default_match_number)

        bat = Bat(user_id=user_id,
                BatterName=BatterName,
                hand=hand, 
                PitchType=PitchType,
                matchnumber=matchnumber,
                place=place,
                Result=Result,
                course=course,
                x=x, y=y, RBI=RBI
                )
        db.session.add(bat)
        db.session.commit()

        session['hand'] = hand
        session['matchnumber'] = matchnumber

        return redirect('/register')

    else:
        return render_template('register.html')


def fetch_query_results():
    # BatとMatchの結合を実行し、Bat.matchnumberで昇順に並び替えた結果を取得します。
    query_results = db.session.query(Bat, Match) \
        .join(Match, Bat.matchnumber == Match.match_number) \
        .order_by(asc(Bat.matchnumber)) \
        .filter_by(user_id=current_user.id) \
        .all()
    return query_results

@app.route("/result")
@login_required
def result():
    bats = db.session.query(Bat.x, Bat.y).filter_by(user_id=current_user.id).all()    # bats_dataを適切なデータに置き換えてください
    bats_xy_list = [[bat.x, bat.y] for bat in bats]
    bats_json = json.dumps(bats_xy_list)
    players = Bat.query.filter_by(user_id=current_user.id).with_entities(Bat.BatterName).distinct().all()

    matchCount = Bat.query.filter_by(user_id=current_user.id).count()
    hitCount = (Bat.query.filter_by(user_id=current_user.id).filter(or_(Bat.Result == '安打', Bat.Result == '二塁打', Bat.Result == '三塁打', Bat.Result == '本塁打')).count())
    doubleCount  = (Bat.query.filter_by(user_id=current_user.id).filter(Bat.Result == '二塁打').count())
    tripleCount  = (Bat.query.filter_by(user_id=current_user.id).filter(Bat.Result == '三塁打').count())
    homerunCount  = (Bat.query.filter_by(user_id=current_user.id).filter(Bat.Result == '本塁打').count())
    ballsCount  = (Bat.query.filter_by(user_id=current_user.id).filter(Bat.Result == '四球').count())
    deadCount  = (Bat.query.filter_by(user_id=current_user.id).filter(Bat.Result == '死球').count())
    bantCount  = (Bat.query.filter_by(user_id=current_user.id).filter(Bat.Result == '犠打').count())
    sacrificeCount  = (Bat.query.filter_by(user_id=current_user.id).filter(Bat.Result == '犠飛').count())
    interferenceCount  = (Bat.query.filter_by(user_id=current_user.id).filter(Bat.Result == '打撃妨害').count())
    batsCount  = (Bat.query.filter_by(user_id=current_user.id).filter(Bat.Result != '').count())
    
    strokeCount  = batsCount - ballsCount - deadCount - bantCount - sacrificeCount - interferenceCount
    NumberOfBaseHit = (hitCount - doubleCount - tripleCount - homerunCount) + doubleCount*2 + tripleCount*3 + homerunCount*4
    if strokeCount != 0:
        BattingAverage   = format(hitCount / strokeCount, '.3f').lstrip('0')
        OnBasePercentage = format((hitCount + ballsCount + deadCount) / (strokeCount + ballsCount + deadCount + sacrificeCount), '.3f').lstrip('0')
        SluggingPercentage = format(NumberOfBaseHit / strokeCount, '.3f').lstrip('0')
        OPS = float(OnBasePercentage) + float(SluggingPercentage)
    else:
        BattingAverage   = 0
        OnBasePercentage = 0
        SluggingPercentage = 0
        OPS = 0
    matches = Match.query.filter_by(user_id=current_user.id).all()
    bat_records = Bat.query.filter_by(user_id=current_user.id).all()

    query_results = fetch_query_results()
    sorted_results = sorted(query_results, key=lambda x: (x[1].date, x[1].opponent), reverse=True)
    grouped_results = groupby(sorted_results, key=lambda x: (x[1].date, x[1].matchType, x[1].opponent))    
    
    return render_template('result.html',
        matchCount=matchCount, 
        hitCount=hitCount, 
        doubleCount=doubleCount, 
        tripleCount=tripleCount, 
        homerunCount=homerunCount, 
        ballsCount=ballsCount, 
        deadCount=deadCount,
        bantCount=bantCount,
        sacrificeCount=sacrificeCount, 
        batsCount=batsCount, 
        strokeCount=strokeCount,
        BattingAverage=BattingAverage,
        OnBasePercentage=OnBasePercentage,
        SluggingPercentage=SluggingPercentage,
        OPS=OPS,
        bats=bats_json,
        players=players,
        matches=matches,
        bat_records=bat_records, 
        grouped_results=grouped_results
        )

from flask import jsonify
@app.route('/api/players')
@login_required
def get_players():
    players = Players.query.filter_by(user_id=current_user.id).all()
    player_list = [{
        'id': player.id, 
        'user_id': player.user_id, 
        'number': player.uniform_number,
        'name': player.player
        } for player in players]
    return jsonify(player_list)

    
@app.route('/api/player-stats')
@login_required
def player_stats():
    player_name = request.args.get('name')
    # 選手名に基づいて成績データをデータベースから取得
    stats = Bat.query.filter_by(BatterName=player_name, user_id=current_user.id).all()
    if stats:
        hitCount = 1 if any(stat.Result in ['安打', '二塁打', '三塁打', '本塁打'] for stat in stats) else 0
        doubleCount = 1 if any(stat.Result == '二塁打' for stat in stats) else 0
        tripleCount = 1 if any(stat.Result == '三塁打' for stat in stats) else 0
        homerunCount = 1 if any(stat.Result == '本塁打' for stat in stats) else 0
        ballsCount = 1 if any(stat.Result == '四球' for stat in stats) else 0
        deadCount = 1 if any(stat.Result == '死球' for stat in stats) else 0
        bantCount = 1 if any(stat.Result == '犠打' for stat in stats) else 0
        sacrificeCount = 1 if any(stat.Result == '犠飛' for stat in stats) else 0
        interferenceCount = 1 if any(stat.Result == '打撃妨害' for stat in stats) else 0
        batsCount = 1 if any(stat.Result != '' for stat in stats) else 0        
        strokeCount = batsCount - ballsCount - deadCount - bantCount - sacrificeCount - interferenceCount
        NumberOfBaseHit = hitCount - doubleCount - tripleCount - homerunCount + doubleCount*2 + tripleCount*3 + homerunCount*4
        BattingAverage = "{:.3f}".format(hitCount / strokeCount if strokeCount else 0).lstrip('0')
        OnBasePercentage = "{:.3f}".format((hitCount + ballsCount + deadCount) / (strokeCount + ballsCount + deadCount + sacrificeCount) if (strokeCount + ballsCount + deadCount + sacrificeCount) else 0).lstrip('0')
        SluggingPercentage = "{:.3f}".format(NumberOfBaseHit / strokeCount if strokeCount else 0).lstrip('0')
        OPS = "{:.3f}".format(float(OnBasePercentage) + float(SluggingPercentage))   
        # 成績データを辞書に変換
        stats_list = [{
            "Result": stat.Result,
            "x": stat.x,
            "y": stat.y,
            "hand": stat.hand,
            "PitchType": stat.PitchType,
            "course": stat.course,
            "RBI": stat.RBI,
            "place": stat.place,
            "matchnumber": stat.matchnumber,
            "hitCount": hitCount,
            "doubleCount": doubleCount,
            "tripleCount": tripleCount,
            "homerunCount": homerunCount,
            "ballsCount": ballsCount,
            "deadCount": deadCount,
            "bantCount": bantCount,
            "sacrificeCount": sacrificeCount,
            "interferenceCount": interferenceCount,
            "batsCount": batsCount,
            "strokeCount": strokeCount,
            "NumberOfBaseHit": NumberOfBaseHit,
            "BattingAverage": BattingAverage,
            "OnBasePercentage": OnBasePercentage,
            "SluggingPercentage": SluggingPercentage,
            "OPS": OPS        
            } for stat in stats]
        return jsonify(stats_list)
    else:
        return jsonify({"error": "Player not found"}), 404

@app.route('/<int:id>/delete', methods=['GET'])
@login_required
def delete(id):
    bat = Bat.query.get(id)
    db.session.delete(bat)
    db.session.commit()
    return redirect('/see')

@app.route('/<int:id>/update', methods=['GET', 'POST'])
@login_required
def update(id):
    bat = Bat.query.get(id)
    if request.method == "GET":
        return render_template("update.html", bat=bat)
    else:
        bat.BatterName= request.form.get('BatterName')
        bat.hand= request.form.get('hand')
        bat.PitchType= request.form.get('PitchType')
        bat.Result= request.form.get('Result')
        bat.course= request.form.get('course')
        bat.x = request.form.get('x')
        bat.y = request.form.get('y')
        bat.RBI = request.form.get('RBI')
        bat.place = request.form.get('place')
        bat.matchnumber = request.form.get('matchnumber')
        
        db.session.commit()
        return redirect('/see')

   
@app.route('/match', methods=['GET', 'POST'])
@login_required
def match():
    if request.method == 'GET':
        matches = Match.query.filter_by(user_id=current_user.id).order_by(Match.id.desc()).all()
        return render_template("match.html", matches=matches)
    if request.method == "POST":
        id= request.form.get('id')
        match_number = request.form.get('match_number')
        user_id= request.form.get('user_id')
        matchType= request.form.get('matchType')
        opponent= request.form.get('opponent')

        # フォームから受け取った日付を取得
        date_str = request.form.get('date')
        # 文字列形式の日付をdateオブジェクトに変換
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

        match = Match(id=id, date=date_obj, user_id=user_id,
                match_number=match_number, matchType=matchType, opponent=opponent)
        db.session.add(match)
        db.session.commit()

        matches = Match.query.filter_by(user_id=current_user.id).order_by(Match.id.desc()).all()

        return render_template('match.html', matches=matches)
    else:
        return render_template('match.html')
    
@app.route('/<int:id>/match_delete', methods=['GET'])
@login_required
def match_delete(id):
    match = Match.query.get(id)
    db.session.delete(match)
    db.session.commit()
    return redirect('/match')

@app.route('/<int:id>/match_update', methods=['GET', 'POST'])
@login_required
def match_update(id):
    match = Match.query.get(id)
    if request.method == "GET":
        return render_template("match_update.html", match=match)
    else:
        match.id = request.form.get('id')
        
        # 日付を文字列からdatetimeオブジェクトに変換
        match.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
        match.MatchType = request.form.get('MatchType')
        match.opponent = request.form.get('opponent')
        
        db.session.commit()
        return redirect('/match')

# ログインページにリダイレクト
@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect('/login')

if __name__ == "__main__":
    app.debug = True
    serve(app, host='localhost', port=8888)
    # app.run('0.0.0.0',port=5000)
    # serve(app, host='0.0.0.0', port=8000)