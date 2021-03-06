from .base36 import *
from ruqqus.classes import *
from flask import g
from sqlalchemy.orm import joinedload

def get_user(username, v=None, nSession=None, graceful=False):

    username=username.replace('\\','')
    username=username.replace('_', '\_')

    if not nSession:
        nSession=g.db
        

    user=nSession.query(User
        ).filter(
        User.username.ilike(username)
        ).first()

    if not user:
        if not graceful:
            abort(404)
        else:
            return None

    if v:
        block=nSession.query(UserBlock).filter(
            or_(
                and_(
                    UserBlock.user_id==v.id, 
                    UserBlock.target_id==user.id
                    ),
                and_(UserBlock.user_id==user.id,
                    UserBlock.target_id==v.id
                    )
                )
            ).first()

        user._is_blocking=block and block.user_id==v.id
        user._is_blocked=block and block.target_id==v.id

    return user

def get_post(pid, v=None, nSession=None, **kwargs):

    i=base36decode(pid)
    
    nSession=nSession or kwargs.get("session")or g.db

    if v:
        vt=nSession.query(Vote).filter_by(user_id=v.id, submission_id=i).subquery()


        items= nSession.query(Submission, vt.c.vote_type
            ).options(
            joinedload(Submission.author).joinedload(User.title)
            ).filter(Submission.id==i).join(
            vt, 
            vt.c.submission_id==Submission.id, 
            isouter=True
            ).first()
        
        if not items:
            abort(404)
        
        x=items[0]
        x._voted=items[1] or 0

    else:
        x=nSession.query(Submission).options(
            joinedload(Submission.author).joinedload(User.title)
            ).filter(Submission.id==i).filter(Submission.id==i).first()

    if not x:
        abort(404)
    return x

def get_posts(pids, sort="hot", v=None):

    if v:
        vt=g.db.query(Vote).filter(Vote.user_id==v.id, Vote.submission_id.in_(pids)).subquery()


        posts= g.db.query(Submission, vt.c.vote_type).options(
            joinedload(Submission.author).joinedload(User.title)
            ).filter(
            Submission.id.in_(pids)
            ).join(
            vt, vt.c.submission_id==Submission.id, isouter=True
            )

        items=[i for i in posts.all()]

        
        posts=[n[0] for n in items]
        for i in range(len(posts)):
            posts[i]._voted=items[i][1] or 0




    else:
        posts=g.db.query(Submission).options(
            joinedload(Submission.author).joinedload(User.title)
            ).filter(
            Submission.id.in_(pids)
            )


        items=[i for i in posts.all()]
        
        posts=[n for n in items]

    posts=sorted(posts, key= lambda x: pids.index(x.id))
    return posts

def get_post_with_comments(pid, sort_type="top", v=None):

    post=get_post(pid, v=v)

    if v:
        votes=g.db.query(CommentVote).filter_by(user_id=v.id).subquery()

        blocking=v.blocking.subquery()

        blocked=v.blocked.subquery()

        comms=g.db.query(
            Comment,
            votes.c.vote_type,
            blocking.c.id,
            blocked.c.id
            ).options(
            joinedload(Comment.author).joinedload(User.title)
            ).filter(
            Comment.parent_submission==post.id,
            Comment.level<=6
            ).join(
            votes,
            votes.c.comment_id==Comment.id,
            isouter=True
            ).join(
            blocking,
            blocking.c.target_id==Comment.author_id,
            isouter=True
            ).join(
            blocked,
            blocked.c.user_id==Comment.author_id,
            isouter=True
            )

        if sort_type=="hot":
            comments=comms.order_by(Comment.score_hot.desc()).all()
        elif sort_type=="top":
            comments=comms.order_by(Comment.score_top.desc()).all()
        elif sort_type=="new":
            comments=comms.order_by(Comment.created_utc.desc()).all()
        elif sort_type=="disputed":
            comments=comms.order_by(Comment.score_disputed.desc()).all()
        elif sort_type=="random":
            c=comms.all()
            comments=random.sample(c, k=len(c))
        else:
            abort(422)


        output=[]
        for c in comments:
            comment=c[0]
            comment._voted=c[1] or 0
            comment._is_blocking=c[2] or 0
            comment._is_blocked=c[3] or 0
            output.append(comment)
        post._preloaded_comments=output

    else:
        comms=g.db.query(
            Comment
            ).options(
            joinedload(Comment.author).joinedload(User.title)
            ).filter(
            Comment.parent_submission==post.id,
            Comment.level<=6
            )

        if sort_type=="hot":
            comments=comms.order_by(Comment.score_hot.desc()).all()
        elif sort_type=="top":
            comments=comms.order_by(Comment.score_top.desc()).all()
        elif sort_type=="new":
            comments=comms.order_by(Comment.created_utc.desc()).all()
        elif sort_type=="disputed":
            comments=comms.order_by(Comment.score_disputed.desc()).all()
        elif sort_type=="random":
            c=comms.all()
            comments=random.sample(c, k=len(c))
        else:
            abort(422)

        output=[c for c in comments]

        post._preloaded_comments=output

    return post


def get_comment(cid, nSession=None, v=None, **kwargs):


    if isinstance(cid, str):
        i=base36decode(cid)
    else: i=cid

    nSession = nSession or kwargs.get('session') or g.db

    if v:
        blocking=v.blocking.subquery()
        blocked=v.blocked.subquery()
        vt=g.db.query(CommentVote).filter(CommentVote.user_id==v.id, CommentVote.comment_id==i).subquery()


        items= g.db.query(Comment, vt.c.vote_type).options(
            joinedload(Comment.author).joinedload(User.title)
            ).filter(
            Comment.id==i
            ).join(
            vt, vt.c.comment_id==Comment.id, isouter=True
            ).first()
        
        if not items:
            abort(404)

        block=nSession.query(UserBlock).filter(
            or_(
                and_(
                    UserBlock.user_id==v.id, 
                    UserBlock.target_id==User.id
                    ),
                and_(UserBlock.user_id==User.id,
                    UserBlock.target_id==v.id
                    )
                )
            ).first()

        x=items[0]
        x._voted=items[1] or 0
        x._is_blocking=block and block.user_id==v.id
        x._is_blocked=block and block.target_id==v.id

    else:
        x=g.db.query(Comment).options(
            joinedload(Comment.author).joinedload(User.title)
            ).filter(Comment.id==i).first()

    if not x:
        abort(404)
    return x

def get_comments(cids, v=None, nSession=None, sort_type="new"):

    if not nSession:
        nSession=g.db

    if v:
        blocking=v.blocking.subquery()
        blocked=v.blocked.subquery()
        vt=nSession.query(CommentVote).filter(CommentVote.user_id==v.id, CommentVote.comment_id.in_(cids)).subquery()


        items= nSession.query(Comment, vt.c.vote_type, blocking.c.id, blocked.c.id).options(joinedload(Comment.post)).filter(
            Comment.id.in_(cids)
            ).options(
            joinedload(Comment.author).joinedload(User.title)
            ).join(
            vt, 
            vt.c.comment_id==Comment.id,
            isouter=True
            ).join(
            blocking,
            blocking.c.target_id==Comment.author_id,
            isouter=True
            ).join(
            blocked,
            blocked.c.user_id==Comment.author_id,
            isouter=True
            ).all()

        output=[]
        for i in items:
        
            x=i[0]
            x._voted=i[1] or 0
            x._is_blocking=i[2] or 0
            x._is_blocked=i[3] or 0
            output.append(x)

    else:
        entries=nSession.query(Comment).options(
            joinedload(Comment.author).joinedload(User.title)
            ).filter(Comment.id.in_(cids)).all()
        output=[]
        for row in entries:
            comment=row[0]
            output.append(comment)

    output=sorted(output, key=lambda x:cids.index(x.id))
    
    return output

def get_board(bid):

    x=g.db.query(Board).filter_by(id=base36decode(bid)).first()
    if not x:
        abort(404)
    return x

def get_guild(name, graceful=False):

    name=name.lstrip('+')

    name=name.replace('\\', '')
    name=name.replace('_','\_')

    x=g.db.query(Board).filter(Board.name.ilike(name)).first()
    if not x:
        if not graceful:
            abort(404)
        else:
            return None
    return x

def get_domain(s):

    #parse domain into all possible subdomains
    parts=s.split(".")
    domain_list=set([])
    for i in range(len(parts)):
        new_domain=parts[i]
        for j in range(i+1, len(parts)):
            new_domain+="."+parts[j]

        domain_list.add(new_domain)

    domain_list=tuple(list(domain_list))

    doms=[x for x in g.db.query(Domain).filter(Domain.domain.in_(domain_list)).all()]

    if not doms:
        return None

    #return the most specific domain - the one with the longest domain property
    doms= sorted(doms, key=lambda x: len(x.domain), reverse=True)

    return doms[0]

def get_title(x):

    title=g.db.query(Title).filter_by(id=x).first()

    if not title:
        abort(400)

    else:
        return title


def get_mod(uid, bid):

    mod=g.db.query(ModRelationship).filter_by(board_id=bid,
                                            user_id=uid,
                                            accepted=True,
                                            invite_rescinded=False).first()

    return mod
