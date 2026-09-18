import hashlib,secrets
from datetime import datetime,timezone,timedelta
from auth import hash_password,verify_password
class AuthService:
    def __init__(self,db): self.db=db
    def _now(self): return datetime.now(timezone.utc)
    def _token_hash(self,token): return hashlib.sha256(token.encode()).hexdigest()
    def register(self,email,password,display_name=''):
        email=email.strip().lower()
        if '@' not in email or '.' not in email.split('@')[-1]: raise ValueError('Enter a valid email address.')
        if self.db.q('SELECT 1 FROM auth_credentials WHERE email=?',(email,)).fetchone(): raise ValueError('An account with this email already exists.')
        uid='u_'+secrets.token_hex(16); now=self._now().isoformat()
        name=(display_name or email.split('@')[0]).strip()[:80] or 'ProjectFit User'
        self.db.q('INSERT INTO users VALUES (?,?,?,?,?,?,?)',(uid,name,None,None,None,'Africa/Johannesburg',now))
        self.db.q('INSERT INTO goals(user_id,objective,target_weight,target_body_fat,training_frequency,calorie_target,protein_target) VALUES(?,?,?,?,?,?,?)',(uid,None,None,None,None,2400,180))
        self.db.q('INSERT INTO privacy_settings VALUES(?,?,?,?,?)',(uid,0,0,0,now))
        self.db.q('INSERT INTO auth_credentials VALUES(?,?,?,?,?,?)',(uid,email,0,hash_password(password),now,now))
        self.db.commit(); return uid
    def login(self,email,password):
        email=email.strip().lower(); row=self.db.q('SELECT * FROM auth_credentials WHERE email=?',(email,)).fetchone()
        if not row or not verify_password(password,row['password_hash']): raise ValueError('Email or password is incorrect.')
        token=secrets.token_urlsafe(48); now=self._now(); exp=now+timedelta(days=30)
        self.db.q('INSERT INTO auth_sessions VALUES(?,?,?,?)',(self._token_hash(token),row['user_id'],now.isoformat(),exp.isoformat())); self.db.commit()
        return token,row['user_id'],exp.isoformat()
    def user_from_token(self,token):
        if not token:return None
        row=self.db.q('SELECT user_id,expires_at FROM auth_sessions WHERE token_hash=?',(self._token_hash(token),)).fetchone()
        if not row:return None
        try:
            if datetime.fromisoformat(row['expires_at']) < self._now():
                self.db.q('DELETE FROM auth_sessions WHERE token_hash=?',(self._token_hash(token),)); self.db.commit(); return None
        except Exception:return None
        return row['user_id']
    def logout(self,token):
        if token:self.db.q('DELETE FROM auth_sessions WHERE token_hash=?',(self._token_hash(token),)); self.db.commit()
    def logout_all(self,uid):
        self.db.q('DELETE FROM auth_sessions WHERE user_id=?',(uid,)); self.db.commit()
    def export_user(self,uid):
        tables=['users','goals','programme','workout_sessions','exercise_logs','workout_derivations','measurements','nutrition_entries','activity_entries','weekly_checkins','weekly_derivations','progress_reviews','privacy_settings']
        out={'export_version':'1.9','user_id':uid,'exported_at':self._now().isoformat(),'data':{}}
        for t in tables:
            cols=[x['name'] for x in self.db.q(f'PRAGMA table_info({t})').fetchall()]
            if t=='users': where,args='id=?',(uid,)
            elif t=='goals' or t=='privacy_settings': where,args='user_id=?',(uid,)
            elif t=='programme': where,args='user_id=?',(uid,)
            elif t=='workout_sessions': where,args='user_id=?',(uid,)
            elif t=='exercise_logs': where,args='session_id IN (SELECT id FROM workout_sessions WHERE user_id=?)',(uid,)
            elif t=='workout_derivations': where,args='exercise_log_id IN (SELECT el.id FROM exercise_logs el JOIN workout_sessions ws ON ws.id=el.session_id WHERE ws.user_id=?)',(uid,)
            elif t=='weekly_derivations': where,args='checkin_id IN (SELECT id FROM weekly_checkins WHERE user_id=?)',(uid,)
            else: where,args='user_id=?',(uid,)
            rows=self.db.q(f'SELECT * FROM {t} WHERE {where}',args).fetchall()
            out['data'][t]={'columns':cols,'rows':[dict(r) for r in rows]}
        return out
    def delete_user(self,uid):
        self.db.q('DELETE FROM users WHERE id=?',(uid,)); self.db.commit()
