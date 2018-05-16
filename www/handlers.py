#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Nina'

"""
url handlers.
"""

import re, time, json, logging, hashlib, base64, asyncio

import markdown2

from aiohttp import web

from coroweb import get, post
from apis import Page, APIError, APIValueError, APIResourceNotFoundError, APIPermissionError

from model import User, Comment, Blog, next_id
from config import configs


COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret


def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p


def user2cookie(user, max_age):
    """
    Generate cookie str by user.
    """
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'),
                filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)


async def cookie2user(cookie_str):
    """
    Parse cookie and load user if cookie is valid.
    """
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None


@get('/')
async def index(*, page='1'):
    logging.debug('index: find all blogs')
    page_index = get_page_index(page)
    total_blogs = await Blog.findNumber('count(id)')
    page = Page(total_blogs, page_index)  # TODO, source code has not page_index?
    if total_blogs == 0:
        blogs = []
    else:
        blogs = await Blog.findAll(orderBy='created_at desc',
                                   limit=(page.offset, page.limit))
    return {
        '__template__': 'blogs.html',
        'page': page,
        'blogs': blogs
    }


@get('/blog/{id}')
async def get_blog(id):
    logging.debug('get_blog: find one blog with id given')
    blog = await Blog.find(id)
    comments = await Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }


@get('/register')
async def register():
    logging.debug('register')
    return {
        '__template__': 'register.html'
    }


@get('/signin')
async def signin():
    logging.debug('signin')
    return {
        '__template__': 'signin.html'
    }


@post('/api/authenticate')
async def authenticate(*, email, passwd):
    logging.debug('authenticate')
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Please input password.')
    users = await User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]
    # check passwd:
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    logging.debug('password from browser: %s' % sha1.hexdigest())
    logging.debug('passwd from database: %s' % user.passwd)
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password.')
    # authenticate ok, set cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@get('/signout')
async def signout(request):
    logging.debug('signout')
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out.')
    return r


@get('/manage/')
async def manage():
    logging.debug('manage')
    return 'redirect:/manage/comments'


@get('/manage/comments')
async def manage_comments(*, page='1'):
    logging.debug('manage_comments')
    return {
        '__template__': 'manage_comments.html',
        'page_index': get_page_index(page)
    }


@get('/manage/blogs')
async def manage_blogs(*, page='1'):
    logging.debug('manager_blogs')
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
    }


@get('/manage/blogs/create')
async def manage_create_blog():
    logging.debug('manage_create_blog')
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }


@get('/manage/blogs/edit')
async def manage_edit_blog(*, id):
    logging.debug('manage_edit_blog')
    return {
        '__template__': 'manage_blog_edit.html',
        'id': id,
        'action': '/api/blogs/%s' % id
    }


@get('/manage/users')
async def manage_users(*, page='1'):
    return {
        '__template__': 'manage_users.html',
        'page_index': get_page_index(page)
    }


@get('/api/comments')
async def api_comments(*, page='1'):
    logging.debug('api_comments')
    page_index = get_page_index(page)
    total_comments = await Comment.findNumber('count(id)')
    p = Page(total_comments, page_index)
    if total_comments == 0:
        return {
            'page': p,
            'comments': []
        }
    comments = await Comment.findAll(orderBy='created_at desc',
                                     limit=(p.offset, p.limit))
    return {
        'page': p,
        'comments': comments
    }


@post('/api/blogs/{id}/comments')
async def api_create_comment(id, request, *, content):
    logging.debug('api_create_comment')
    if request.__user__ is None:
        raise APIPermissionError('Please sign in.')
    if not content or not content.strip():
        raise APIValueError('content')
    blog = await Blog.find(id)
    if blog is None:
        raise APIResoourceNotFoundError('Blog')
    comment = Comment(blog_id=blog.id,
                      user_id=request.__user__.id,
                      user_name=request.__user__.name,
                      user_image=request.__user__.image,
                      content=content.strip())
    await comment.save()
    return comment


@post('/api/comments/{id}/delete')
async def api_delete_comments(id, request):
    logging.debug('api_delete_comments')
    check_admin(request)
    c = await Comment.find(id)
    if c is None:
        raise APIResourceNotFoundError('Comment')
    await c.remove()
    return {
        'id': id
    }


@get('/api/users')
async def api_get_users(request, *, page='1'):
    logging.debug('api_get_users')
    # TODO, users' info should be protected.
    # if not check, anyone without signin can get users' info via '/api/users'
    check_admin(request)
    page_index = get_page_index(page)
    total_users = await User.findNumber('count(id)')
    p = Page(total_users, page_index)
    if total_users == 0:
        return {
            'page': p,
            'users': []
        }
    users = await User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    for u in users:
        u.passwd = '******'
    return {
        'page': p,
        'users': users
    }


_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')


@post('/api/users')
async def api_register_user(*, email, name, passwd):
    logging.debug('api_register_user')
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = await User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email,
                passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
                image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    await user.save()
    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@get('/api/blogs')
async def api_blogs(*, page='1'):
    logging.debug('api_blogs: find all blogs')
    page_index = get_page_index(page)
    total_blogs = await Blog.findNumber('count(id)')
    p = Page(total_blogs, page_index)
    if total_blogs == 0:
        return {
            'page': p,
            'blogs': []
        }
    blogs = await Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return {
        'page': p,
        'blogs': blogs
    }


@get('/api/blogs/{id}')
async def api_get_blog(*, id):
    logging.debug('api_get_blog: find one blog with id given')
    blog = await Blog.find(id)
    return blog


@post('/api/blogs')
async def api_create_blog(request, *, name, summary, content):
    logging.debug('api_create_blog')
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog = Blog(user_id=request.__user__.id,
                user_name=request.__user__.name,
                user_image=request.__user__.image,
                name=name.strip(),
                summary=summary.strip(),
                content=content.strip())
    await blog.save()
    return blog


@post('/api/blogs/{id}')
async def api_update_blog(id, request, *, name, summary, content):
    logging.debug('api_update_blog')
    check_admin(request)
    blog = await Blog.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    await blog.update()
    return blog


@post('/api/blogs/{id}/delete')
async def api_delete_blog(request, *, id):
    logging.debug('api_delete_blog')
    check_admin(request)
    blog = await Blog.find(id)
    await blog.remove()
    return dict(id=id)






