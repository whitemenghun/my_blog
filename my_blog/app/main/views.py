from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app, make_response, session, g
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries
from datetime import datetime
from sqlalchemy import and_, or_

from . import main
from .forms import CommentForm
from .. import db
from ..models import User, Post, Comment, Tag, Category, Link


@main.before_app_request
def before_request():
    categories = Category.query.all()
    links = Link.query.all()
    about = User.query.get(1).about_me
    g.categories = categories
    g.links = links
    g.about = about


@main.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    keyword = request.args.get('keyword', None)
    if keyword:
        pagination = db.session.query(Post).filter(
            or_(Post.tittle.like(f'%{keyword}%'),
                Post.body.like(f'%{keyword}%'))).paginate(page,
                                                          per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
                                                          error_out=False)
        posts = pagination.items
    return render_template('index.html', posts=posts, pagination=pagination)


# 分类
@main.route('/category/post/<id>')
def category(id):
    star_posts = Post.query.all()
    category = Category.query.get(id)
    posts = Post.query.filter_by(category_id=id)
    return render_template('category.html', category=category, star_posts=star_posts, posts=posts)


@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    posts = Post.query.all()
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          email=form.email.data,
                          post=post,
                          name=form.name.data)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been published.')
        return redirect(url_for('.post', id=post.id, page=-1))
    return render_template('post.html', post=post, posts=posts, form=form)
