import hashlib,secrets
from datetime import datetime,timezone,timedelta
from supabase_auth import SupabaseAuth
from cloud_sync import CloudSync,table_rows,restore_rows

class CloudAccountService:
    def __init__(self,db,app): self.db=db; self.app=app; self.auth=SupabaseAuth(); self.cloud=CloudSync()
    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _hash(self,t): return hashlib.sha256(t.encode()).hexdigest()
    def _session(self,access,refresh,uid,expires_in=3600):
        token=secrets.token_urlsafe(48); exp=datetime.now(timezone.utc)+timedelta(seconds=int(expires_in or 3600))
        self.db.q('INSERT OR REPLACE INTO cloud_sessions(token_hash,user_id,access_token,refresh_token,created_at,expires_at) VALUES(?,?,?,?,?,?)',(self._hash(token),uid,access,refresh,self._now(),exp.isoformat())); self.db.commit(); return token,exp
    def ensure_local_user(self,user):
        uid=user['id']; row=self.db.q('SELECT id FROM users WHERE id=?',(uid,)).fetchone()
        if not row:
            name=(user.get('user_metadata') or {}).get('display_name') or (user.get('email','').split('@')[0] or 'ProjectFit User')
            self.db.q('INSERT INTO users VALUES (?,?,?,?,?,?,?)',(uid,name[:80],None,None,None,'Africa/Johannesburg',self._now()))
            self.db.q('INSERT INTO goals(user_id,objective,target_weight,target_body_fat,training_frequency,calorie_target,protein_target) VALUES(?,?,?,?,?,?,?)',(uid,None,None,None,None,2400,180))
            self.db.q('INSERT INTO privacy_settings VALUES(?,?,?,?,?)',(uid,0,0,0,self._now()))
            try:
                from service import PROGRAMME
                for w in range(1,13):
                    for day,(session,exs) in PROGRAMME.items():
                        for ex,sets,rr,kg,rir,rest in exs:
                            self.db.q('INSERT INTO programme(user_id,week,day,session,exercise,sets,rep_range,start_weight,rir,rest_seconds) VALUES(?,?,?,?,?,?,?,?,?,?)',(uid,w,day,session,ex,sets,rr,kg,rir,rest))
            except Exception: pass
            self.db.commit()
        return uid
    def signup(self,email,password,name,redirect_to=None):
        data=self.auth.signup(email,password,name,redirect_to)
        if not data.get('session'): return {'authenticated':False,'verification_required':True,'message':'Account created. Check your email to verify your account, then log in.'}
        return self._finish(data)
    def resend_confirmation(self,email,redirect_to=None):
        return self.auth.resend(email,redirect_to)
    def login(self,email,password): return self._finish(self.auth.login(email,password))
    def _finish(self,data):
        user=data.get('user') or self.auth.user(data['access_token']); uid=self.ensure_local_user(user)
        tok,exp=self._session(data['access_token'],data.get('refresh_token'),uid,data.get('expires_in',3600))
        return {'authenticated':True,'session_cookie':tok,'user':{'id':uid,'email':user.get('email'),'display_name':(user.get('user_metadata') or {}).get('display_name') or user.get('email','').split('@')[0],'email_verified':bool(user.get('email_confirmed_at'))}}
    def token_from_cookie(self,cookie):
        if not cookie:return None
        return self.db.q('SELECT * FROM cloud_sessions WHERE token_hash=?',(self._hash(cookie),)).fetchone()
    def user_id(self,cookie):
        row=self.token_from_cookie(cookie); return row['user_id'] if row else None
    def access(self,cookie):
        row=self.token_from_cookie(cookie)
        if not row:return None
        try:
            if row['expires_at'] and datetime.fromisoformat(row['expires_at']) <= datetime.now(timezone.utc)+timedelta(seconds=30):
                if row['refresh_token']:
                    data=self.auth.refresh(row['refresh_token']); exp=datetime.now(timezone.utc)+timedelta(seconds=int(data.get('expires_in',3600)))
                    self.db.q('UPDATE cloud_sessions SET access_token=?,refresh_token=?,expires_at=? WHERE token_hash=?',(data['access_token'],data.get('refresh_token') or row['refresh_token'],exp.isoformat(),row['token_hash'])); self.db.commit(); return data['access_token']
                return None
        except Exception:return None
        return row['access_token']
    def logout(self,cookie):
        row=self.token_from_cookie(cookie)
        if row:
            try:self.auth.logout(row['access_token'])
            except Exception:pass
            self.db.q('DELETE FROM cloud_sessions WHERE token_hash=?',(row['token_hash'],)); self.db.commit()
    def logout_all(self,uid):
        rows=self.db.q('SELECT access_token FROM cloud_sessions WHERE user_id=?',(uid,)).fetchall()
        for r in rows:
            try:self.auth.logout(r['access_token'])
            except Exception:pass
        self.db.q('DELETE FROM cloud_sessions WHERE user_id=?',(uid,)); self.db.commit()
    def sync(self,cookie):
        row=self.token_from_cookie(cookie); uid=row['user_id'] if row else None; token=self.access(cookie)
        if not uid or not token: raise PermissionError('Cloud session expired. Please log in again.')
        remote=self.cloud.pull(uid,token); local=table_rows(self.db,uid); local_ids={r['id'] for r in local}
        for rr in remote:
            if rr['id'] not in local_ids and self.db.q('SELECT 1 FROM cloud_record_state WHERE record_id=?',(rr['id'],)).fetchone():
                try:self.cloud._req('/rest/v1/pf_records?id=eq.'+rr['id']+'&user_id=eq.'+uid,'DELETE',token=token,prefer='return=minimal'); self.db.q('DELETE FROM cloud_record_state WHERE record_id=?',(rr['id'],))
                except Exception: pass
        accepted=[]; conflicts=[]
        for rec in local:
            st=self.db.q('SELECT server_version FROM cloud_record_state WHERE record_id=?',(rec['id'],)).fetchone(); base=int(st['server_version']) if st else 0
            a,c=self.cloud.upsert(uid,token,rec,base)
            if a: accepted.append(a); self.db.q('INSERT OR REPLACE INTO cloud_record_state VALUES(?,?,?)',(rec['id'],a['version'],self._now()))
            elif c: conflicts.append(c)
        remote=self.cloud.pull(uid,token)
        if not conflicts and remote:
            restore_rows(self.db,uid,remote)
            for r in remote:self.db.q('INSERT OR REPLACE INTO cloud_record_state VALUES(?,?,?)',(r['id'],int(r['version']),self._now()))
            self.db.commit()
        return {'ok':True,'user_id':uid,'uploaded':len(accepted),'downloaded':len(remote),'conflicts':conflicts,'synced_at':self._now()}
    def pull_only(self,cookie):
        row=self.token_from_cookie(cookie); uid=row['user_id'] if row else None; token=self.access(cookie)
        if not uid or not token: raise PermissionError('Cloud session expired. Please log in again.')
        remote=self.cloud.pull(uid,token); restore_rows(self.db,uid,remote)
        for r in remote:self.db.q('INSERT OR REPLACE INTO cloud_record_state VALUES(?,?,?)',(r['id'],int(r['version']),self._now()))
        self.db.commit(); return {'ok':True,'downloaded':len(remote)}
    def delete_account(self,cookie):
        row=self.token_from_cookie(cookie); uid=row['user_id'] if row else None; token=self.access(cookie)
        if not uid or not token: raise PermissionError('Cloud session expired.')
        self.cloud.delete_all(uid,token); self.db.q('DELETE FROM users WHERE id=?',(uid,)); self.db.commit(); self.logout(cookie); return {'ok':True}
    def export_cloud(self,cookie):
        row=self.token_from_cookie(cookie); uid=row['user_id'] if row else None; token=self.access(cookie)
        if not uid or not token: raise PermissionError('Cloud session expired.')
        return {'export_version':'2.2','user_id':uid,'exported_at':self._now(),'records':self.cloud.pull(uid,token)}
