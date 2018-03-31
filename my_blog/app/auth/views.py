from flask import render_template, redirect, request, url_for, flash, json, current_app, abort, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import time

from . import auth
from .. import db
from ..models import User, Category, Tag, Post, Comment, Link
from ..email import send_email
from .forms import LoginForm


@auth.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('.admin_manage'))
        flash('账号或密码错误.')
    return render_template('auth/login.html', form=form)


@auth.route('/logout/')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('.admin_manage'))


@auth.route('/')
@auth.route('/manage/')
@login_required
def admin_manage():
    posts = Post.query.all()
    categories = Category.query.all()
    tags = Tag.query.all()
    return render_template('auth/admin.html', posts=posts, categories=categories, tags=tags)


@auth.route('/about_me')
@login_required
def about_me():
    about = request.args.get('about', '')
    if about:
        u = User.query.get(1)
        u.about_me = about
        db.session.add(u)
        return redirect(url_for('.admin_manage'))
    name = request.args.get(('lkname', ''))
    link = request.args.get('lk', None)
    if link:
        lk = Link(name=name, link=link)
        db.session.add(lk)
        return redirect(url_for('.admin_manage'))
    return render_template('auth/about-me.html')


# 新建类别或修改类别
@auth.route('/newcategory/', methods=['POST', 'GET'])
@auth.route('/ecategory/<int:id>/', methods=['POST', 'GET'])
@login_required
def add_category(id=None):
    category = Category() if not id else Category.query.get(id)
    if request.method == 'POST':
        if not id:
            category = Category(category_name=request.form.get('category'))
            db.session.add(category)
        else:
            category = Category.query.get(id)
            category.category_name = request.form.get('category')
        db.session.commit()
        return redirect(url_for('.admin_manage'))
    return render_template('auth/newcategory.html', category=category)


# 新建
@auth.route('/newpost')
@login_required
def newpost():
    categories = Category.query.all()
    return render_template('auth/newpost.html', categories=categories)


# 添加
@auth.route('/addpost', methods=['POST'])
@login_required
def addpost():
    global filepath
    if request.method == 'POST':
        tagtemp = []
        taglist = request.form['tags'].split(',')
        for i in taglist:
            tagtemp.append(Tag(name=i))
        file = request.files.get('imgFile', None)
        if file and allowed_file(file.filename):
            filename = str(int(time.time())) + '_' + secure_filename(file.filename)
            filepath = current_app.config['UPLOAD_FOLDER'] + filename
            file.save(filepath)
        db.session.add(Post(tags=tagtemp, body=request.form['content'], tittle=request.form['title'],
                            tags_name=request.form['tags'], category_id=request.form.get('category'),
                            photo=filepath, isstar=request.form.get('star', False)))
        db.session.commit()
    return redirect(url_for('.newpost'))


# 检查封面图片是否允许上传
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in current_app.config['ALLOWED_EXTENSIONS']


@auth.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        file = request.files.get('imgFile', None)
        if file and allowed_file(file.filename):
            filename = str(int(time.time())) + '_' + secure_filename(file.filename)
            file.save(current_app.config['UPLOAD_FOLDER'] + filename)
            data = {'error': 0, 'url': current_app.config['UPLOAD_FOLDER'] + filename}
            return json.dumps(data)
    return 'FAIL!'


@auth.route('/epost', methods=['GET'])
@auth.route('/epost/<int:id>')
@login_required
def epost(id=None):
    num = request.args.get('post', '')
    categories = Category.query.all()
    if id:
        p = Post.query.get(id)
        return render_template('auth/editpost.html', p=p, categories=categories)
    if num:
        p = Post.query.get_or_404(num)
        return render_template('auth/editpost.html', p=p, categories=categories)
    abort(404)


@auth.route('/apost', methods=['POST'])
@login_required
def apost():
    if request.method == 'POST':
        p = Post.query.filter_by(id=request.form['num']).first()
        p.title = request.form['title']
        p.body = request.form['content']
        p.isstar = request.form.get('star', False)
        p.category_id = request.form.get('category')
        db.session.commit()
    return redirect(url_for('.admin_manage'))


# 评论列表
@auth.route('/comment/list/')
@login_required
def comment_list():
    comments = Comment.query.all()
    return render_template('auth/comment-list.html', comments=comments)


# 管理评论
@auth.route('/comment/able/<int:id>')
@login_required
def comment_able(id):
    comment = Comment.query.get(id)
    if comment.disabled:
        comment.disabled = False
    else:
        comment.disabled = True
    db.session.add(comment)
    return redirect(url_for('.comment_list'))


# 回复评论
@auth.route('/comment/reply/<int:id>')
def comment_reply(id):
    comment = Comment.query.get(id)
    message = request.args.get('message', None)
    if message:
        comment.reply = message
        send_email(comment.email, '评论回复', 'auth/email/reply', message=message, comment=comment)
        db.session.add(comment)
        return redirect(url_for('.comment_list'))
    return render_template('auth/comment-reply.html', comment=comment)


# 删除类别
@auth.route('/dcategory/<int:id>')
@login_required
def dcategory(id):
    c = Category.query.get(id)
    if c:
        db.session.delete(c)
        db.session.commit()
    return redirect(url_for('.admin_manage'))


# 删除文章
@auth.route('/dpost/<int:id>')
@login_required
def dpost(id):
    p = Post.query.get(id)
    if p:
        db.session.delete(p)
        db.session.commit()
    return redirect(url_for('.admin_manage'))


# 删除标签
@auth.route('/dtag/<int:id>')
@login_required
def dtag(id):
    t = Tag.query.get(id)
    if t:
        db.session.delete(t)
        db.session.commit()
    return redirect(url_for('.admin_manage'))
