#!/usr/bin/env python

import os
import sys
import cgi
import json
import tagdb
import datetime
import urllib


config = tagdb.load_config()
form = cgi.FieldStorage()
user = tagdb.auth(form)
if not user:
    print "Content-type: text/html\r\n"
    print '''error: user'''
    sys.exit(-1)


if 'createzip' in form and int(form.getvalue('createzip')) > 0:
    filename = tagdb.createzip(user)
    print "Status: 303 See other"
    print "Location: %s" % (filename)
    print #empty line to indicate end of header
    exit()

#content type declaration after the potential redirect
print "Content-type: text/html\r\n"

if 'done' in form:
    done = int(form.getvalue('done'))
else:
    done = -1

filtered = 'filter' in form and int(form.getvalue('filter'))
if 'sort' in form:
    sort = form.getvalue('sort')
else:
    sort = 'title'
if 'order' in form:
    sort_rev = form.getvalue('order') == 'reversed'
else:
    sort_rev = False

papers = tagdb.parse_bibtex()
msg = ""

if 'init' in form and int(form.getvalue('init')) > 0:
    tagdb.init_assignment(user, int(form.getvalue('init')))
    msg = "papers reset and reassigned"

if filtered:
    sm = '<a href="?user=%s&done=%d">show all</a>' % (user, done)
else:
    sm = '<a href="?user=%s&filter=1&done=%s">show my assignments</a>' % (user, done)

if done < 0:
    view_cb = ['all']
else:
    view_cb = ['<a href="?user=%s&filter=%d&done=-1">all</a>' % (user, filtered)]
for j, cb in enumerate(config['done']):
    if done == j:
        view_cb.append(cb)
    else:
        view_cb.append('<a href="?user=%s&filter=%d&done=%d">%s</a>' % (user, filtered, j, cb))

edit_cb = []
for j, cb in enumerate(config['edit']):
    edit_cb.append('<a href="config.py?user=%s&edit=%s">%s</a>' % (user, cb[0], cb[1]))
if len(edit_cb):
    edit_cb = "edit: " + ' | '.join(edit_cb)
else:
    edit_cb = ""

print '''<!DOCTYPE html>
<html>
<head>
<title>Paper tag list</title>
<link href="style.css" rel="stylesheet" />
</head>
<body>
<nav>%s | show: %s<div style="float:right">%s 
| <form method="post" name="reinit" action="?user=%s" style="display:inline"><input type="hidden" name="init" value="1"><a href="#" onclick="javascript:if(confirm('(re)initialize assignments?'))document.forms['reinit'].submit();return false;">initialize assignments</a></form> 
| <form method="post" name="download" action="?user=%s" style="display:inline"><input type="hidden" name="createzip" value="1"><a href="#" onclick="javascript:if(confirm('Re-create zip and download?'))document.forms['download'].submit();return false;">download tag data</a></form></div></nav>
''' % (sm, ' | '.join(view_cb), edit_cb, user, user )

if msg != "":
    print '''<div class="msg">%s</div>''' % (msg)


def nice_dt(d):
    if d.days >= 500:
        return "never"
    if d.days >= 7:
        return str(d.days / 7) + " week" + "s" * (d.days >= 14)
    if d.days >= 1:
        return str(d.days) + " day" + "s" * (d.days >= 2)
    if d.seconds >= 60 * 60:
        return str(d.seconds / 60 / 60) + " hour" + "s" * (d.seconds >= 60 * 60)
    if d.seconds >= 60:
        return str(d.seconds / 60) + " minute" + "s" * (d.seconds >= 120)
    return "now"


now = datetime.datetime.utcnow()
render = []
mecnt = 0
ptc = 0
auth_stat = {}
for item in papers:
    m = tagdb.get_meta(item['pid'])
    if not m[0] in auth_stat:
        auth_stat[m[0]] = [0] * len(config['done'])
    m[3] = max(0, min(m[3], len(config['done']) - 1))
    auth_stat[m[0]][m[3]] += 1
    if (filtered == 0 or m[0] == user) and (m[3] == done or done < 0):
        if m[3] != 1: ptc += 1
        if m[0] == '':
            bgc = ' style="background-color:#fcc"'
        else:
            bgc = ''
        if m[0] == user:
            unf = ' style="background-color:#aaa"'
            mecnt += 1
        else:
            unf = ''
        render.append([item, unf, bgc, m[0], m[1], m[2], nice_dt(now - m[2]), config['done'][m[3]], m[4], m[5], m[6]])

if done < 0:
    assigned = '''%d papers in total (%.0f%% touched)''' % (len(render), 100.0 * ptc / len(render))
else:
    assigned = '''%d <em>%s</em> papers assigned to %s (%d total papers)''' % (mecnt, config['done'][done], user, len(render))

print '''<h1>All papers</h1>
<div class="info">%s<br/>
<a href="#leaderboard">detailed breakdown</a></div>
<br/><br/>
<table>
<tr>
    <th class="exp"><a href="?user=%s&filter=%d&done=%d&sort=title">title</a></th>
    <th class="nexp"><a href="?user=%s&filter=%d&done=%d&sort=doi">doi</a></th>
    <th class="nexp">scholar</th>
    <th class="nexp">action</th>
    <th class="nexp">PDF</th>
    <th class="nexp"><a href="?user=%s&filter=%d&done=%d&sort=3">assigned</a></th>
    <th class="nexp"><a href="?user=%s&filter=%d&done=%d&sort=8">last change</a></th>
    <th class="nexp"><a href="?user=%s&filter=%d&done=%d&sort=4">last user</a></th>
    <th class="nexp"><a href="?user=%s&filter=%d&done=%d&sort=7">progress</a></th>
    <th class="nexp"><a href="?user=%s&filter=%d&done=%d&sort=9&order=reversed">rating</a></th>
</tr>''' % (assigned,
            user, filtered, done, user, filtered, done, user, filtered, done,
            user, filtered, done, user, filtered, done, user, filtered, done,
            user, filtered, done)

ptc = len(papers) - sum([v[1] for v in auth_stat.values()])
if len(sort) == 1:
    render.sort(key=lambda x:x[int(sort)], reverse=sort_rev)
else:
    render.sort(key=lambda x:x[0][sort], reverse=sort_rev)
for r in render:
    scholar = urllib.quote(r[0]['title'] + ' ' + r[0]['doi'])
    if r[10] == '':
      pdf = 'no PDF'
    else:
      pdf = '<a href="%s">download</a>' % r[10]
    print '''<tr>
    <td class="exp">%s</td>
    <td class="nexp"%s><a href="https://doi.org/%s">link</a></td>
    <td class="nexp"%s><a href="https://scholar.google.com/scholar?hl=en&q=%s&btnG=">scholar</a></td>
    <td class="nexp"%s><a href="edit.py?user=%s&pid=%s">edit</a></td>
    <td class="nexp"%s>%s</td>
    <td class="nexp"%s%s>%s</td>
    <td class="nexp"%s>%s</td>
    <td class="nexp"%s>%s</td>
    <td class="nexp"%s>%s</td>
    <td class="nexp"%s>%s</td>
</tr>''' % (r[0]['title'], r[1], r[0]['doi'], r[1], scholar, r[1], user, r[0]['pid'], r[1], pdf, r[2], r[1], r[3], r[1], r[6], r[1], r[4], r[1], r[7], r[1], r[9])

if len(render) == 0:
    print '''<tr>
    <td class="exp" style="font-style:italic;text-align:center">no papers to show</td>
    <td class="nexp"></td>
    <td class="nexp"></td>
    <td class="nexp"></td>
    <td class="nexp"></td>
    <td class="nexp"></td>
    <td class="nexp"></td>
    <td class="nexp"></td>
    <td class="nexp"></td>
    <td class="nexp"></td>
</tr>'''

print '''
</table>
<br/><br/>
<h1 id="leaderboard">Summary</h1>
<div class="info">%.0f%% of all papers touched</div><br/>
<table id="summary">
  <tr><th class="summary_left"></th>''' % (ptc * 100.0 / len(papers)) + ''.join(['<th>%s</th>' % s for s in config['done']]) + '''<th>touched</th><th>total</th></tr>'''
for un in sorted(auth_stat.keys(), key=lambda x:sum(auth_stat[x]) - auth_stat[x][1], reverse=True):
    print '  <tr><td class="summary_left">%s</td>' % un + ''.join(['<td>%d</td>' % i for i in auth_stat[un]]) + '<td>%d</td><td>%d</td></tr>' % (sum(auth_stat[un]) - auth_stat[un][1], sum(auth_stat[un]))
print '  <tr style="background-color:#aaa"><td class="summary_left">sum</td>' + ''.join(['<td>%d</td>' % sum([v[i] for v in auth_stat.values()]) for i in range(len(config['done']))]) + '<td>%d</td><td>%d</td></tr>' % (ptc, len(papers))
print '''</table>
</body>
</html>'''
